"""Atomic fixed-price Pokemon purchases using existing wallets and transfers."""

from contextlib import contextmanager
from datetime import timedelta
import hashlib
import json
from uuid import UUID, uuid4

from django.db.models import Case, Value, When
from django.utils import timezone

from pokemon.services.battle_rewards import BattleRewards
from pokemon.services.ownership import (
    OwnershipError, OwnershipTransfers, PokemonReservations, acting_character,
    assert_character_free, assert_transferable, fresh_owned, locked_owners,
)
from pokemon.services.placement import PlacementService
from pokemon.services.trade_snapshot import PokemonTradeSnapshot
from pokemon.services.trading import TradeOffers


class Marketplace:
    """Reserve hatched owned Pokemon; never mint money or award progression."""

    lifetime = timedelta(hours=24)
    maximum_price = 1_000_000
    maximum_wallet = 2_147_483_647

    def __init__(self, actor, *, clock=None):
        """Use the acting character's current wallet/storage, never account-wide funds."""
        self.actor = acting_character(actor)
        self.actor_id = self.actor.pk
        self.clock = clock or timezone.now

    @staticmethod
    def identifier(value):
        """Reject malformed IDs without disclosing or mutating unrelated listings."""
        try:
            return UUID(str(value))
        except (TypeError, ValueError) as error:
            raise OwnershipError("Use the full listing ID from +market.") from error

    def create(self, selector, price, *, request_id=None):
        """Publish a fixed-price snapshot and exclusive claim in one transaction."""
        from pokemon.models.market import MarketListing

        if type(price) is not int or not 1 <= price <= self.maximum_price:
            raise OwnershipError("Choose a whole price from 1 to 1,000,000 using existing trainer money.")
        listing_id = self.identifier(request_id) if request_id is not None else uuid4()
        with locked_owners((self.actor_id,)) as (characters, storages, _):
            existing = MarketListing.objects.select_for_update().filter(pk=listing_id).first()
            if existing:
                if (existing.seller_character_id != self.actor_id or existing.price != price
                        or existing.request_selector != selector.strip().lower()):
                    raise OwnershipError("That request identity belongs to different listing terms.")
                return existing
            pokemon_id = TradeOffers.select(self.actor_id, selector)
            source = fresh_owned(pokemon_id, lock=True)
            storage = storages[self.actor_id]
            source, placement = PlacementService(storage)._pokemon(source, storage)
            assert_transferable(characters[self.actor_id], source, placement)
            if source.is_egg:
                raise OwnershipError("The beta marketplace lists hatched Pokemon only. Eggs may use consent trading.")
            listing = MarketListing.objects.create(id=listing_id, seller_id=self.actor_id,
                seller_character_id=self.actor_id, seller_name=self.actor.key,
                pokemon=source, owned_id=source.pk, price=price,
                request_selector=selector.strip().lower(), snapshot=PokemonTradeSnapshot.capture(source.pk), expires_at=self.clock() + self.lifetime)
            PokemonReservations(self.actor).claim("market", [source.pk], listing.pk)
            return listing

    @contextmanager
    def locked(self, listing_id, *, purchase=False):
        """Lock stable owners/storage/wallets before the listing and its asset."""
        from pokemon.models.market import MarketListing

        listing_id = self.identifier(listing_id)
        row = MarketListing.objects.filter(pk=listing_id).values("seller_character_id").first()
        if row is None:
            raise OwnershipError("No such marketplace listing.")
        if not purchase and row["seller_character_id"] != self.actor_id:
            raise OwnershipError("Only this character's own listings can be cancelled or reclaimed.")
        owner_ids = (row["seller_character_id"], self.actor_id) if purchase else (self.actor_id,)
        with locked_owners(owner_ids) as owners:
            listing = MarketListing.objects.select_for_update().get(pk=listing_id)
            yield listing, owners

    @staticmethod
    def _claim(listing):
        """A missing/conflicting claim is an integrity error, never guessed safe."""
        from pokemon.models.ownership import PokemonReservation

        claim = PokemonReservation.objects.filter(pokemon_id=listing.owned_id, kind="market", token=listing.pk,
            storage__user_id=listing.seller_character_id).first()
        if claim is None:
            raise OwnershipError("This listing's reservation needs staff review; no money or ownership changed.")
        return claim

    def close(self, listing_id, *, expired_only=False):
        """Release exactly this seller/listing claim; retry never moves an asset."""
        with self.locked(listing_id) as (listing, _):
            if listing.state != "active":
                return listing
            expired = listing.expires_at <= self.clock()
            if expired_only and not expired:
                return listing
            self._claim(listing).delete()
            listing.state = "expired" if expired else "cancelled"
            listing.closed_at = self.clock()
            listing.save(update_fields=["state", "closed_at"])
            return listing

    def mine(self):
        """Reclaim expired claims on the owner's ordinary reconnect/status route."""
        from pokemon.models.market import MarketListing

        for identifier in MarketListing.objects.filter(seller_character_id=self.actor_id, state="active",
                expires_at__lte=self.clock()).values_list("pk", flat=True):
            self.close(identifier, expired_only=True)
        return list(MarketListing.objects.filter(seller_character_id=self.actor_id).order_by(Case(When(state="active", then=Value(0)), default=Value(1)), "-created_at")[:30])

    def browse(self):
        """Public listing snapshots never expose a buyer's future live asset state."""
        from pokemon.models.market import MarketListing

        return list(MarketListing.objects.filter(state="active", expires_at__gt=self.clock()).order_by("created_at")[:30])

    @staticmethod
    def _digest(listing):
        """Review binds price, seller and exact advertised asset state."""
        return hashlib.sha256(json.dumps({"listing": str(listing.pk), "seller": listing.seller_character_id,
            "price": listing.price, "snapshot": listing.snapshot}, sort_keys=True).encode()).hexdigest()

    def inspect(self, listing_id):
        """Show published terms and bind the current character's review to them."""
        from pokemon.models.market import MarketListing

        listing = MarketListing.objects.filter(pk=self.identifier(listing_id)).first()
        if listing is None:
            raise OwnershipError("No such marketplace listing.")
        if listing.state == "active":
            with locked_owners((self.actor_id,)):
                self.actor.attributes.add("market_review:" + str(listing.pk), self._digest(listing), category="market_reviews")
        return self.describe(listing)

    def buy(self, listing_id):
        """Debit/credit and reuse the common transfer or roll everything back."""
        from pokemon.models.market import MarketListing
        from pokemon.models.trainer import Trainer

        listing_id = self.identifier(listing_id)
        prior = MarketListing.objects.filter(pk=listing_id).first()
        if prior is None:
            raise OwnershipError("No such marketplace listing.")
        if prior.state == "sold" and prior.buyer_character_id == self.actor_id:
            return prior.receipt
        if prior.seller_character_id == self.actor_id:
            raise OwnershipError("You cannot buy your own listing.")
        if prior.state != "active":
            raise OwnershipError("That listing is no longer available.")
        result = None
        expired = False
        with self.locked(listing_id, purchase=True) as (listing, (characters, storages, trainers)):
            if listing.state == "sold" and listing.buyer_character_id == self.actor_id:
                return listing.receipt
            if listing.state != "active":
                raise OwnershipError("That listing is no longer available.")
            if listing.expires_at <= self.clock():
                self._claim(listing).delete()
                listing.state, listing.closed_at = "expired", self.clock()
                listing.save(update_fields=["state", "closed_at"])
                expired = True
            else:
                for character in characters.values():
                    assert_character_free(character)
                if type(listing.snapshot.get("summary", {}).get("shiny")) is not bool:
                    raise OwnershipError("This older listing did not record shiny state. The seller must cancel and relist before purchase.")
                reviewed = BattleRewards.stored_attribute(self.actor, "market_review:" + str(listing.pk), category="market_reviews")
                if reviewed != self._digest(listing):
                    raise OwnershipError(f"Inspect the exact price and Pokemon first: +market inspect {listing.pk}.")
                source = fresh_owned(listing.owned_id, lock=True)
                if source.trainer_id != trainers[listing.seller_character_id].pk:
                    raise OwnershipError("The listed Pokemon no longer belongs to that seller.")
                if PokemonTradeSnapshot.capture(source.pk)["fingerprint"] != listing.snapshot["fingerprint"]:
                    raise OwnershipError("The advertised Pokemon changed. Seller must cancel and publish fresh terms.")
                buyer, seller = trainers[self.actor_id], trainers[listing.seller_character_id]
                if buyer.money < listing.price:
                    raise OwnershipError("You do not have enough trainer money for this listing.")
                if seller.money > self.maximum_wallet - listing.price:
                    raise OwnershipError("The seller's wallet cannot receive this payment; no money changed.")
                self._claim(listing).delete()
                # The seller's immutable public listing is its explicit authority
                # to sell this exact asset at this price; this buyer supplies the
                # other approval through the purchase request. No user can submit
                # approvals for another character via the trade command.
                transfer = OwnershipTransfers(characters[listing.seller_character_id], clock=self.clock).prepare(
                    self.actor_id, [{"pokemon": source.pk, "source": listing.seller_character_id,
                                     "destination": self.actor_id}], purpose="market")
                service = OwnershipTransfers(self.actor, clock=self.clock)
                service.approve(transfer.pk)
                settlement = service.commit(transfer.pk)
                Trainer.objects.filter(pk=buyer.pk).update(money=buyer.money - listing.price)
                Trainer.objects.filter(pk=seller.pk).update(money=seller.money + listing.price)
                listing.state, listing.closed_at = "sold", self.clock()
                listing.buyer_id = listing.buyer_character_id = self.actor_id
                listing.purchase_id = uuid4()
                listing.receipt = {"purchase": str(listing.purchase_id), "listing": str(listing.pk),
                    "buyer": self.actor_id, "seller": listing.seller_character_id, "price": listing.price,
                    "transfer": settlement, "buyer_money": buyer.money - listing.price,
                    "seller_money": seller.money + listing.price}
                listing.save(update_fields=["state", "closed_at", "buyer", "buyer_character_id", "purchase_id", "receipt"])
                result = listing.receipt
        if expired:
            raise OwnershipError("That listing expired. Its reservation was released; no money or Pokemon changed.")
        return result

    def describe(self, listing):
        """Render only the seller-approved snapshot and clear wallet/expiry rules."""
        summary = listing.snapshot["summary"]
        state = "expired" if listing.state == "active" and listing.expires_at <= self.clock() else listing.state
        outcome = ""
        if listing.state == "sold" and self.actor_id in (listing.seller_character_id, listing.buyer_character_id):
            wallet = listing.receipt["buyer_money" if self.actor_id == listing.buyer_character_id else "seller_money"]
            destination = listing.receipt["transfer"]["pokemon"][0]
            outcome = (f"\nPurchase {listing.purchase_id}; saved wallet after this sale: {wallet}. "
                       f"Pokemon destination: character #{destination['owner']}, {destination['location']}, "
                       f"slot {destination['slot']}, box {destination['box']}, position {destination['position']}. "
                       "This is the historical receipt; later activity can change current location or money.")
        moves = ", ".join(f"{move['name']} (PP {move['pp'] if move['pp'] is not None else 'full'})"
                          for move in summary.get("moves", [])) or "none"
        return (f"Listing {listing.pk}: {state}\n{summary['name']} ({summary['species']}, level {summary['level']}) "
                f"[{listing.owned_id}], holding {summary.get('held_item') or 'nothing'}.\n"
                f"Seller: {listing.seller_name} (#{listing.seller_character_id}); price: {listing.price} trainer money, no fee.\n"
                f"Expires {listing.expires_at.isoformat()}.\nIVs: {summary.get('ivs')}; EVs: {summary.get('evs')}; "
                f"ability {summary.get('ability')}; nature {summary.get('nature')}; HP {summary.get('current_hp') if summary.get('current_hp') is not None else 'full'}; "
                f"status {summary.get('status') or 'healthy'}.\n"
                f"Shiny: {'unrecorded; seller must cancel/relist' if type(summary.get('shiny')) is not bool else 'yes' if summary['shiny'] else 'no'}; Tera: {summary.get('tera_type')}; friendship: {summary.get('friendship')}.\n"
                f"Hyper Training: {summary.get('hyper_training')}; moves: {moves}.\n"
                f"Mint stats: {summary.get('trained_stat_nature', 'unrecorded') or 'none'} (genetic Nature unchanged).\n"
                f"Use +market buy {listing.pk} after inspection, or +market cancel {listing.pk} if you are the seller. "
                "Full parties use a box; purchases do not heal, grant EXP or trigger evolution." + outcome)

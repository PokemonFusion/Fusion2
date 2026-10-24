"""Private durable player offers over the shared ownership transfer service."""

from contextlib import contextmanager
import hashlib
import json
from uuid import uuid4

from django.db import transaction
from django.db.models import Case, Q, Value, When
from django.utils import timezone

from pokemon.services.battle_rewards import BattleRewards
from pokemon.services.ownership import OwnershipError, OwnershipTransfers, acting_character, fresh_owned, locked_owners


class TradeOffers:
    """Offer one owned asset; counter with one owned asset to negotiate a swap."""

    def __init__(self, actor, *, clock=None):
        """Bind every operation to the active character rather than its account."""
        self.actor = acting_character(actor)
        self.actor_id = self.actor.pk
        self.clock = clock or timezone.now
        self.transfers = OwnershipTransfers(actor, clock=self.clock)

    @contextmanager
    def _locked(self, operation_id):
        """Public trade authority cannot approve or close an internal market settlement."""
        with self.transfers.locked(operation_id) as (operation, locked):
            if operation.purpose != "trade":
                raise OwnershipError("Use the marketplace receipt for this market settlement.")
            yield operation, locked

    def recipient(self, query):
        """Resolve only an exact player character name or database character ID."""
        from evennia.objects.models import ObjectDB

        query = query.strip()
        players = ObjectDB.objects.filter(trainer__isnull=False, userstorage__isnull=False,
                                          db_typeclass_path="pokemon.user.User")
        if query.startswith("#") and query[1:].isdigit():
            players = players.filter(pk=int(query[1:]))
        else:
            players = players.filter(db_key__iexact=query)
        ids = list(players.values_list("pk", flat=True)[:2])
        if len(ids) != 1 or ids[0] == self.actor_id:
            raise OwnershipError("Choose another player's exact character name or #character ID.")
        return ids[0]

    @staticmethod
    def select(character_id, selector):
        """Read a canonical party slot or a unique owned UUID prefix, including boxes."""
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.storage import PokemonPlacement

        selector = selector.strip().lower()
        number = selector.removeprefix("slot").strip()
        if number in {"1", "2", "3", "4", "5", "6"}:
            identifier = PokemonPlacement.objects.filter(storage__user_id=character_id,
                location_type="party", slot=int(number)).values_list("pokemon_id", flat=True).first()
            if identifier:
                return identifier
            raise OwnershipError("There is no Pokemon in that party slot.")
        compact = selector.replace("-", "")
        if not 8 <= len(compact) <= 32 or any(value not in "0123456789abcdef" for value in compact):
            raise OwnershipError("Use a party slot or at least eight characters of an owned Pokemon UUID from +box/+sheet.")
        ids = [identifier for identifier in OwnedPokemon.objects.filter(trainer__user_id=character_id).values_list("pk", flat=True)
               if str(identifier).replace("-", "").startswith(compact)]
        if len(ids) != 1:
            raise OwnershipError("That Pokemon ID does not uniquely identify one of your owned Pokemon.")
        return ids[0]

    def propose(self, recipient_query, selector):
        """Reserve the proposer's own selected asset; transfer requires acceptance."""
        recipient_id = self.recipient(recipient_query)
        with locked_owners((self.actor_id, recipient_id)):
            identifier = self.select(self.actor_id, selector)
            operation = self.transfers.prepare(recipient_id, [{"pokemon": identifier,
                "source": self.actor_id, "destination": recipient_id}])
            self._notice(operation, "offered a Pokemon trade")
            return operation

    def counter(self, operation_id, selector):
        """Replace an offer with new immutable terms and invalidate prior consent."""
        with self._locked(operation_id) as (operation, _):
            if operation.recipient_id != self.actor_id:
                raise OwnershipError("Only the intended recipient may counter this offer.")
            if operation.state != "pending" or operation.expires_at <= self.clock():
                raise OwnershipError("That offer is closed or expired. Start a new offer.")
            self._require_review(operation)
            partner_assets = [move for move in operation.terms if move["source"] == operation.proposer_id]
            if len(partner_assets) != 1:
                raise OwnershipError("The player trade route supports one offered Pokemon per character.")
            identifier = self.select(self.actor_id, selector)
            partner = operation.proposer_id
            old_asset = partner_assets[0]["pokemon"]
            from pokemon.services.trade_snapshot import PokemonTradeSnapshot

            fresh_owned(old_asset, lock=True)
            if (not partner_assets[0].get("snapshot") or PokemonTradeSnapshot.capture(old_asset)["fingerprint"]
                    != partner_assets[0]["snapshot"]["fingerprint"]):
                raise OwnershipError("The original offered Pokemon changed. Cancel it and request a new offer before countering.")
            replacement_id = uuid4()
            self.transfers.cancel(operation.pk, reason="countered", replacement_id=replacement_id)
            replacement = self.transfers.prepare(partner, [
                {"pokemon": identifier, "source": self.actor_id, "destination": partner},
                {"pokemon": old_asset, "source": partner, "destination": self.actor_id},
            ], request_id=replacement_id)
            self._notice(replacement, "countered with new trade terms")
            return replacement

    def accept(self, operation_id):
        """The named recipient accepts the sealed snapshot and atomically commits."""
        with self._locked(operation_id) as (operation, _):
            if operation.recipient_id != self.actor_id:
                raise OwnershipError("Wait for the intended recipient to accept your offer.")
            if operation.state != "completed":
                if operation.state != "pending" or operation.expires_at <= self.clock():
                    raise OwnershipError("That offer is closed or expired; cancel expired offers to release reservations.")
                self._require_review(operation)
            if not all(move.get("snapshot") for move in operation.terms):
                raise OwnershipError("This older offer has no displayed asset snapshot. Cancel it and make a new offer.")
            was_completed = operation.state == "completed"
            self.transfers.approve(operation.pk)
            receipt = self.transfers.commit(operation.pk)
            if not was_completed:
                self._notice(operation, "accepted and completed the trade")
            return receipt

    def close(self, operation_id, *, decline=False):
        """Persist a participant-bound decline/cancellation, including expired claims."""
        with self._locked(operation_id) as (operation, _):
            if decline and operation.recipient_id != self.actor_id:
                raise OwnershipError("Only the intended recipient may decline this offer.")
            was_pending = operation.state == "pending"
            result = self.transfers.cancel(operation.pk, reason="declined" if decline else "cancelled")
            if was_pending:
                self._notice(result, "closed the trade")
            return result

    def _notice(self, operation, message):
        """Notify only the other participant after commit; receipts survive offline use."""
        from evennia.objects.models import ObjectDB

        other_id = operation.recipient_id if self.actor_id == operation.proposer_id else operation.proposer_id
        def publish():
            """A disconnected transport must not roll back a completed operation."""
            other = ObjectDB.objects.get(pk=other_id)
            other.msg(f"Character #{self.actor_id} {message}. Use +trade inspect {operation.pk}; +trade lists your offers and receipts.")
        transaction.on_commit(publish, robust=True)

    def offers(self):
        """Discover this character's pending and recent receipts after reconnect."""
        from pokemon.models.ownership import OwnershipTransfer

        return list(OwnershipTransfer.objects.filter(Q(proposer_id=self.actor_id) | Q(recipient_id=self.actor_id), purpose="trade")
                    .order_by(Case(When(state="pending", then=Value(0)), default=Value(1)), "-created_at")[:30])

    def list_line(self, operation):
        """Keep discovery compact; closing pending offers exposes older entries."""
        state = "expired; cancel to release" if operation.state == "pending" and operation.expires_at <= self.clock() else operation.state
        partner = operation.recipient if operation.proposer_id == self.actor_id else operation.proposer
        return f"{operation.pk}: {state}, with {partner.key}. Use +trade inspect {operation.pk}."

    def inspect(self, operation_id):
        """Render only immutable offered summaries and the persisted outcome."""
        with self._locked(operation_id) as (operation, _):
            if operation.state == "pending" and operation.recipient_id == self.actor_id:
                self.actor.attributes.add("trade_review:" + str(operation.pk), self._digest(operation), category="trade_reviews")
            return self.describe(operation)

    @staticmethod
    def _digest(operation):
        """Bind the recipient's displayed-terms review to the immutable offer."""
        return hashlib.sha256(json.dumps(operation.terms, sort_keys=True).encode()).hexdigest()

    def _require_review(self, operation):
        """Neither an old offer nor another character's review substitutes for consent."""
        if any(type(move.get("snapshot", {}).get("summary", {}).get("shiny")) is not bool for move in operation.terms):
            raise OwnershipError("This older offer did not record shiny state. Cancel it and make a new offer before consent.")
        reviewed = BattleRewards.stored_attribute(self.actor, "trade_review:" + str(operation.pk), category="trade_reviews")
        if reviewed != self._digest(operation):
            raise OwnershipError(f"Inspect these exact terms first: +trade inspect {operation.pk}. Then accept or counter this offer.")

    def describe(self, operation):
        """Keep ownership IDs explicit and never reveal future live asset changes."""
        state = operation.state
        if state == "pending" and operation.expires_at <= self.clock():
            state = "expired; cancel to release reservations"
        lines = [f"Trade {operation.pk}: {state}",
                 f"{operation.proposer.key} (#{operation.proposer_id}) and {operation.recipient.key} "
                 f"(#{operation.recipient_id}); expires {operation.expires_at.isoformat()}"]
        for move in operation.terms:
            snapshot = move.get("snapshot", {})
            summary = snapshot.get("summary", {})
            held = summary.get("held_item") or "nothing"
            lines.append(f"#{move['source']} offers {summary.get('name', move['pokemon'])} "
                         f"({summary.get('species', 'unrecorded species')}, level {summary.get('level', '?')}, "
                         f"{'egg' if summary.get('is_egg') else summary.get('gender', '?')}, holding {held}) "
                         f"[{move['pokemon']}] to #{move['destination']}.")
            if summary:
                lines.append(f"  {summary.get('ability')}, {summary.get('nature')} nature; "
                             f"{'unrecorded shiny state' if type(summary.get('shiny')) is not bool else 'shiny' if summary['shiny'] else 'not shiny'}; Tera {summary.get('tera_type') or 'native'}; "
                             f"HP {summary.get('current_hp') if summary.get('current_hp') is not None else 'full'}, "
                             f"status {summary.get('status') or 'healthy'}; friendship {summary.get('friendship')}.")
                lines.append(f"  HP/Atk/Def/SpA/SpD/Spe genetic IVs: {summary.get('ivs')}; EVs: {summary.get('evs')}; "
                             f"Hyper Training: {', '.join(summary.get('hyper_training', [])) or 'none'}.")
                lines.append("  Active moves: " + (", ".join(
                    f"{value['slot']}: {value['name']} (PP {value['pp'] if value['pp'] is not None else 'full'})"
                    for value in summary.get("moves", [])) or "none") + ".")
        if operation.state == "pending":
            if any(type(move.get("snapshot", {}).get("summary", {}).get("shiny")) is not bool for move in operation.terms):
                lines.append("This older offer did not record shiny state. Cancel it and make a new offer; it cannot be accepted or countered.")
            lines.append("Automatic destination: a free party slot, otherwise your box. No fees or automatic evolution.")
            lines.append(f"Recipient: +trade accept {operation.pk} or +trade counter {operation.pk}=<your slot/UUID>. "
                         f"Use +trade decline {operation.pk} or +trade cancel {operation.pk} to close it.")
        elif operation.state == "completed":
            lines.append("Completed. Repeating acceptance returns this same receipt and never trades again.")
        elif operation.result:
            lines.append(f"Closed by #{operation.result.get('closed_by')}: {operation.result.get('reason', state)}.")
            if operation.result.get("replacement"):
                lines.append("Replacement offer: " + operation.result["replacement"] + ". Previous consent does not apply.")
        return "\n".join(lines)

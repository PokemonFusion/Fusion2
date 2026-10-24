"""Character-authorized, atomic ownership transfers over canonical placement.

Compound writers lock character IDs, storage IDs, trainer IDs, the operation,
then Pokemon IDs in sorted order. Same-owner writers keep the storage-first contract;
they must never acquire a character lock after acquiring storage.
"""

from contextlib import contextmanager
from datetime import timedelta
from uuid import UUID, uuid4

from django.db import transaction
from django.utils import timezone

from pokemon.services.battle_rewards import BattleRewards
from pokemon.services.placement import PlacementError, PlacementService


class OwnershipError(PlacementError):
    """A rejected ownership operation leaves assets, approvals and money intact."""


def acting_character(actor):
    """Bind authority to a real character, never a coincident account integer PK."""
    from evennia.accounts.models import AccountDB
    from evennia.objects.models import ObjectDB

    character = BattleRewards.character(actor)
    if isinstance(actor, AccountDB) or not isinstance(character, ObjectDB) or not character.pk:
        raise OwnershipError("Use this route as your active character.")
    return character


def fresh_owned(pokemon_id, *, lock=False):
    """Bypass Evennia's identity map before checking or publishing model fields."""
    from pokemon.models.core import OwnedPokemon

    query = OwnedPokemon.objects
    if lock:
        query = query.select_for_update()
    row = query.values().get(pk=pokemon_id)
    pokemon = OwnedPokemon.objects.get(pk=pokemon_id)
    for key, value in row.items():
        setattr(pokemon, key, value)
    pokemon._state.fields_cache.clear()
    for key in ("_cached_stats", "_prefetched_objects_cache", "_pf2_active_fusion",
                "_pf2_fusion_kind", "_pf2_fusion_xp", "_pf2_fusion_level"):
        pokemon.__dict__.pop(key, None)
    return pokemon


def assert_unreserved(pokemon_id, *, token=None, operation="placement"):
    """Shared storage/Fusion/item guard; caller must already hold storage's lock."""
    from pokemon.models.ownership import PokemonReservation

    reservation = PokemonReservation.objects.filter(pokemon_id=pokemon_id).values("kind", "token").first()
    if reservation and (token is None or str(reservation["token"]) != str(token)):
        raise OwnershipError(f"Pokemon is reserved for {reservation['kind']}. Finish or cancel that activity first.")
    from pokemon.services.necrozma_guards import assert_operation

    assert_operation(pokemon_id, operation)


def assert_character_free(character):
    """Read saved battle references rather than a potentially stale Attribute cache."""
    from utils.locks import _has_active_battle_ref

    if (any(_has_active_battle_ref(BattleRewards.stored_attribute(character, key))
            for key in ("battle_lock", "battle_id", "pvp_locked"))
            or getattr(character.ndb, "battle_instance", None)):
        raise OwnershipError("Finish your battle before transferring or reserving Pokemon.")


def fusion_references(character):
    """Normalize saved Fusion UUIDs for every custody guard, including old starters."""
    active = BattleRewards.stored_attribute(character, "fusion_id")
    forms = BattleRewards.stored_attribute(character, "fusion_forms") or []
    if isinstance(forms, dict):
        forms = list(forms.values())
    elif isinstance(forms, (str, bytes)):
        forms = [forms]
    if not isinstance(forms, (list, tuple)):
        raise OwnershipError("Invalid saved Fusion references; ask staff to inspect them.")
    references = set()
    for value in [active, *forms]:
        if value:
            try:
                references.add(str(UUID(str(value))))
            except (ValueError, TypeError):
                references.add(str(value))
    return references


def claim_battle(character, battle_id):
    """Serialize roster admission with transfer, storage and reservation writers.

    Take the character before storage, as every compound ownership writer does.
    NPCs without owned storage have no transferable roster. Saved locks protect
    the interval between admission and construction of runtime snapshots.
    """
    from pokemon.models.storage import UserStorage
    from evennia.objects.models import ObjectDB

    with transaction.atomic():
        ObjectDB.objects.select_for_update(no_key=True).filter(pk=character.pk).values("pk").get()
        storage = UserStorage.objects.select_for_update().filter(user_id=character.pk).first()
        if storage is not None:
            for key in ("battle_lock", "battle_id"):
                existing = BattleRewards.stored_attribute(character, key)
                if existing is not None and existing is not False and existing != "" and str(existing) != str(battle_id):
                    raise OwnershipError("Finish your current battle first.")
            for placement in storage.placements.filter(location_type="party").order_by("pokemon_id"):
                PlacementService(storage)._pokemon(placement.pokemon, storage, operation="battle")
            active = BattleRewards.stored_attribute(character, "fusion_id")
            if active:
                from django.core.exceptions import ValidationError
                from pokemon.models.core import OwnedPokemon

                try:
                    pokemon = fresh_owned(active, lock=True)
                    _, placement = PlacementService(storage)._pokemon(pokemon, storage)
                except (OwnedPokemon.DoesNotExist, ValueError, ValidationError) as error:
                    raise OwnershipError("Your saved Fusion needs staff review before battling.") from error
                # Old chargen recorded permanent forms while retaining a party
                # slot. They remain owner-checked, unavailable for transfer, and
                # are normalized by the next atomic Fusion transition (#723).
                kind = BattleRewards.stored_attribute(character, "fusion_kind")
                compatible_party = placement is not None and placement.location_type == "party" and kind in (None, "permanent")
                if placement is None or (placement.location_type != "fusion" and not compatible_party):
                    raise OwnershipError("Your saved Fusion placement needs staff review before battling.")
        character.attributes.reset_cache()
        character.attributes.add("battle_lock", battle_id)


def assert_transferable(character, pokemon, placement, *, token=None):
    """Reject battle, Fusion, eggs in progress and conflicting system claims."""
    assert_character_free(character)
    if placement is None or placement.location_type not in ("party", "box"):
        raise OwnershipError("Pokemon must be in your party or a box and cannot be reserved for Fusion.")
    if str(pokemon.pk) in fusion_references(character):
        raise OwnershipError("Pokemon is reserved for an active or unlocked Fusion form.")
    if any(str(flag).lower() in {"breeding", "breeding_parent", "carrying_egg"}
           for flag in (pokemon.flags or [])):
        raise OwnershipError("Pokemon has a breeding reservation; contact staff if it is stale.")
    assert_unreserved(pokemon.pk, token=token)


@contextmanager
def locked_owners(character_ids):
    """Lock both owners before any asset, including empty destination storage."""
    from evennia.objects.models import ObjectDB
    from pokemon.models.storage import UserStorage
    from pokemon.models.trainer import Trainer

    ids = sorted(set(character_ids))
    with transaction.atomic():
        # NO KEY UPDATE still serializes all compound writers, but permits the
        # FK key-share locks taken by Attribute inserts in storage-first routes.
        rows = list(ObjectDB.objects.select_for_update(no_key=True).filter(pk__in=ids).order_by("pk").values_list("pk", flat=True))
        storages = list(UserStorage.objects.select_for_update().filter(user_id__in=ids).order_by("pk"))
        trainers = list(Trainer.objects.select_for_update().filter(user_id__in=ids).order_by("pk"))
        if rows != ids or len(storages) != len(ids) or len(trainers) != len(ids):
            raise OwnershipError("Every participant needs their own existing character, trainer and storage.")
        yield ({pk: ObjectDB.objects.get(pk=pk) for pk in ids},
               {storage.user_id: storage for storage in storages},
               {trainer.user_id: trainer for trainer in trainers})


class PokemonReservations:
    """Exclusive claims shared by marketplace, Daycare and breeding services.

    The calling system owns its durable cycle/payment receipt and token. This
    layer grants no payment, advancement or automatic custody repair. Trade uses
    OwnershipTransfers so a token alone can never substitute for both approvals.
    """

    def __init__(self, actor):
        """Bind authority to the current character's own storage."""
        self.actor_id = acting_character(actor).pk

    def claim(self, kind, pokemon_ids, token):
        """Atomically reserve fresh eligible assets or reject the entire batch."""
        from pokemon.models.ownership import PokemonReservation
        from pokemon.models.core import OwnedPokemon

        if kind not in {"market", "daycare", "breeding"}:
            raise OwnershipError("Use the owning system's supported reservation route.")
        try:
            token = UUID(str(token))
            ids = sorted({UUID(str(value)) for value in pokemon_ids})
        except (ValueError, TypeError) as error:
            raise OwnershipError("Invalid reservation identity.") from error
        if not 1 <= len(ids) <= 12:
            raise OwnershipError("Reserve between one and twelve Pokemon at a time.")
        with locked_owners((self.actor_id,)) as (characters, storages, _):
            storage = storages[self.actor_id]
            claims = []
            for pokemon_id in ids:
                try:
                    pokemon = fresh_owned(pokemon_id, lock=True)
                except OwnedPokemon.DoesNotExist as error:
                    raise OwnershipError("No such owned Pokemon.") from error
                pokemon, placement = PlacementService(storage)._pokemon(pokemon, storage, reservation_token=token)
                assert_transferable(characters[self.actor_id], pokemon, placement, token=token)
                reservation, _ = PokemonReservation.objects.get_or_create(
                    pokemon=pokemon, defaults={"storage": storage, "kind": kind, "token": token})
                if reservation.kind != kind or reservation.token != token:
                    raise OwnershipError("Pokemon is reserved for a different activity.")
                claims.append(reservation)
            return claims

    def release(self, kind, token):
        """Release only this character's matching system/cycle; retries are no-ops."""
        from pokemon.models.ownership import PokemonReservation

        if kind not in {"market", "daycare", "breeding"}:
            raise OwnershipError("Trade reservations need the consent transfer route.")
        try:
            token = UUID(str(token))
        except (ValueError, TypeError) as error:
            raise OwnershipError("Invalid reservation identity.") from error
        with locked_owners((self.actor_id,)) as (_, storages, _):
            return PokemonReservation.objects.filter(storage=storages[self.actor_id], kind=kind, token=token).delete()[0]


class OwnershipTransfers:
    """Prepare immutable offers, collect explicit consent and commit exact retries."""

    lifetime = timedelta(minutes=15)

    def __init__(self, actor, *, clock=None):
        """Use the acting character, never the account's other characters."""
        self.actor = acting_character(actor)
        self.actor_id = self.actor.pk
        self.clock = clock or timezone.now

    def _terms(self, recipient_id, movements):
        """Normalize bounded two-character asset terms, including destination policy."""
        if (not isinstance(recipient_id, int) or isinstance(recipient_id, bool)
                or recipient_id == self.actor_id):
            raise OwnershipError("Choose another character as recipient.")
        if not isinstance(movements, (tuple, list)) or not 1 <= len(movements) <= 12:
            raise OwnershipError("A transfer needs between one and twelve Pokemon.")
        parties = {self.actor_id, recipient_id}
        terms = []
        try:
            for move in movements:
                source, destination = move["source"], move["destination"]
                if (type(source) is not int or type(destination) is not int
                        or {source, destination} != parties):
                    raise OwnershipError("Only the two named characters may exchange assets.")
                mode = move.get("mode", "auto")
                slot = move.get("slot")
                if mode not in ("auto", "party", "box"):
                    raise OwnershipError("Choose automatic placement, party or box.")
                if slot is not None and (mode != "party" or type(slot) is not int or slot not in range(1, 7)):
                    raise OwnershipError("A destination party slot must be between 1 and 6.")
                terms.append({"pokemon": str(UUID(str(move["pokemon"]))), "source": source,
                              "destination": destination, "mode": mode, "slot": slot})
        except (KeyError, ValueError, TypeError, AttributeError) as error:
            if isinstance(error, OwnershipError):
                raise
            raise OwnershipError("Invalid transfer terms.") from error
        if len({move["pokemon"] for move in terms}) != len(terms):
            raise OwnershipError("Each Pokemon may appear only once.")
        if self.actor_id not in {move["source"] for move in terms}:
            raise OwnershipError("You must offer at least one of your own Pokemon.")
        return sorted(terms, key=lambda move: move["pokemon"])

    @staticmethod
    def _participant(operation, actor_id):
        """Owning the same login account does not grant another character's consent."""
        if actor_id not in (operation.proposer_id, operation.recipient_id):
            raise OwnershipError("That transfer does not belong to this character.")

    @contextmanager
    def locked(self, operation_id):
        """Read immutable participant IDs, then serialize owners and the operation."""
        from pokemon.models.ownership import OwnershipTransfer

        try:
            operation_id = UUID(str(operation_id))
            owners = OwnershipTransfer.objects.values("proposer_id", "recipient_id").get(pk=operation_id)
        except (ValueError, TypeError, OwnershipTransfer.DoesNotExist) as error:
            raise OwnershipError("No such transfer for this character.") from error
        if self.actor_id not in owners.values():
            raise OwnershipError("That transfer does not belong to this character.")
        with locked_owners(owners.values()) as locked:
            operation = OwnershipTransfer.objects.select_for_update().get(pk=operation_id)
            self._participant(operation, self.actor_id)
            yield operation, locked

    def _assets(self, operation, locked):
        """Freshly lock all Pokemon in UUID order and verify source custody."""
        from pokemon.models.core import OwnedPokemon

        characters, storages, _ = locked
        for character in characters.values():
            assert_character_free(character)
        assets = []
        for move in operation.terms:
            try:
                pokemon = fresh_owned(move["pokemon"], lock=True)
            except OwnedPokemon.DoesNotExist as error:
                raise OwnershipError("An offered Pokemon no longer exists.") from error
            source = storages[move["source"]]
            pokemon, placement = PlacementService(source)._pokemon(pokemon, source, reservation_token=operation.pk)
            assert_transferable(characters[move["source"]], pokemon, placement, token=operation.pk)
            if move.get("snapshot"):
                from pokemon.services.trade_snapshot import PokemonTradeSnapshot

                if PokemonTradeSnapshot.capture(pokemon.pk)["fingerprint"] != move["snapshot"]["fingerprint"]:
                    raise OwnershipError("An offered Pokemon changed since these terms were recorded. Cancel and make a new offer.")
            assets.append((move, pokemon, placement))
        return assets

    @staticmethod
    def _reserve(operation, assets, owner_ids):
        """Reserve only assets whose owner has explicitly approved these terms."""
        from pokemon.models.ownership import PokemonReservation

        for move, pokemon, placement in assets:
            if move["source"] in owner_ids:
                reservation, _ = PokemonReservation.objects.get_or_create(
                    pokemon=pokemon, defaults={"storage": placement.storage, "kind": "trade",
                                               "token": operation.pk, "transfer": operation})
                if reservation.token != operation.pk:
                    raise OwnershipError("Pokemon is already reserved for another activity.")

    def prepare(self, recipient_id, movements, *, request_id=None, purpose="trade"):
        """Create a retryable offer without granting the recipient's consent."""
        from pokemon.models.ownership import OwnershipTransfer

        if purpose not in {"trade", "market"}:
            raise OwnershipError("Unknown transfer purpose.")
        terms = self._terms(recipient_id, movements)
        try:
            operation_id = UUID(str(request_id)) if request_id is not None else uuid4()
        except (ValueError, TypeError) as error:
            raise OwnershipError("Invalid request identity.") from error
        with locked_owners((self.actor_id, recipient_id)) as locked:
            existing = OwnershipTransfer.objects.select_for_update().filter(pk=operation_id).first()
            if existing:
                if (existing.proposer_id != self.actor_id or existing.recipient_id != recipient_id or existing.purpose != purpose
                        or [{key: value for key, value in move.items() if key != "snapshot"}
                            for move in existing.terms] != terms):
                    raise OwnershipError("Request identity already belongs to different transfer terms.")
                return existing
            from pokemon.services.trade_snapshot import PokemonTradeSnapshot

            operation = OwnershipTransfer(
                id=operation_id, proposer_id=self.actor_id, recipient_id=recipient_id, purpose=purpose,
                terms=terms, approvals=[self.actor_id], expires_at=self.clock() + self.lifetime)
            assets = self._assets(operation, locked)
            for move, pokemon, _ in assets:
                move["snapshot"] = PokemonTradeSnapshot.capture(pokemon.pk)
            operation.save(force_insert=True)
            self._reserve(operation, assets, {self.actor_id})
            return operation

    def approve(self, operation_id):
        """Consent is character-specific and covers exactly the persisted terms."""
        with self.locked(operation_id) as (operation, locked):
            if operation.state == "completed":
                return operation
            if operation.state != "pending" or operation.expires_at <= self.clock():
                raise OwnershipError("That offer is closed or expired; cancel it to release its reservations.")
            assets = self._assets(operation, locked)
            approvals = sorted(set([*operation.approvals, self.actor_id]))
            self._reserve(operation, assets, set(approvals))
            operation.approvals = approvals
            operation.save(update_fields=["approvals"])
            return operation

    def cancel(self, operation_id, *, reason="cancelled", replacement_id=None):
        """Close exact pending terms and retain the actor/reason in a sealed receipt."""
        if reason not in {"cancelled", "declined", "countered"}:
            raise OwnershipError("Unknown cancellation reason.")
        with self.locked(operation_id) as (operation, _):
            if operation.state == "pending":
                operation.reservations.all().delete()
                operation.state = "expired" if operation.expires_at <= self.clock() else "cancelled"
                operation.result = {"closed_by": self.actor_id,
                                    "reason": "expired" if operation.state == "expired" else reason}
                if replacement_id is not None:
                    operation.result["replacement"] = str(UUID(str(replacement_id)))
                operation.save(update_fields=["result", "state"])
            return operation

    def commit(self, operation_id):
        """Move all assets and mirrors or none; replay returns an immutable receipt."""
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.storage import ActivePokemonSlot

        touched = []
        try:
            with self.locked(operation_id) as (operation, locked):
                if operation.state == "completed":
                    return operation.result
                if operation.state != "pending" or operation.expires_at <= self.clock():
                    raise OwnershipError("That offer is closed or expired; cancel it to release its reservations.")
                if set(operation.approvals) != {operation.proposer_id, operation.recipient_id}:
                    raise OwnershipError("Both characters must approve these exact terms first.")
                assets = self._assets(operation, locked)
                _, storages, trainers = locked
                # Free every outgoing slot before allocating incoming members of a
                # full-party swap. The outer transaction never publishes this state.
                for move, pokemon, placement in assets:
                    touched.append(pokemon.pk)
                    ActivePokemonSlot.objects.filter(pokemon=pokemon).delete()
                    pokemon.stored_users.clear()
                    pokemon.boxes.clear()
                    placement.location_type = "fusion"
                    placement.slot = placement.box_id = placement.box_position = None
                    placement.save()
                result = []
                for move, pokemon, placement in assets:
                    destination = storages[move["destination"]]
                    OwnedPokemon.objects.filter(pk=pokemon.pk).update(trainer_id=trainers[move["destination"]].pk)
                    pokemon = fresh_owned(pokemon.pk)
                    placement.pokemon = pokemon
                    placement.storage = destination
                    service = PlacementService(destination)
                    use_party = move["mode"] == "party" or (
                        move["mode"] == "auto" and destination.placements.filter(location_type="party").count() < 6)
                    if use_party:
                        placed = service._party(pokemon, destination, placement, move["slot"], allow_fusion=True)
                    else:
                        placed = service._box(pokemon, destination, placement, allow_fusion=True)
                    result.append({"pokemon": str(pokemon.pk), "owner": move["destination"],
                                   "location": placed.location_type, "slot": placed.slot,
                                   "box": placed.box_id, "position": placed.box_position})
                operation.reservations.all().delete()
                operation.result = {"transfer": str(operation.pk), "pokemon": result}
                operation.completed_at = self.clock()
                operation.state = "completed"
                operation.save(update_fields=["result", "completed_at", "state"])
                return operation.result
        finally:
            # A failed savepoint must not leave a SharedMemoryModel with phantom
            # ownership. Outer rollback callers must refresh/flush again at exit.
            for pokemon_id in touched:
                from django.db import connection

                if OwnedPokemon.objects.filter(pk=pokemon_id).exists():
                    if connection.in_atomic_block:
                        OwnedPokemon.flush_cached_instance(OwnedPokemon.objects.get(pk=pokemon_id))
                        transaction.on_commit(lambda pid=pokemon_id: self._publish(pid))
                    else:
                        self._publish(pokemon_id)

    @staticmethod
    def _publish(pokemon_id):
        """A subsequent legitimate release cannot invalidate a committed receipt."""
        from pokemon.models.core import OwnedPokemon

        try:
            fresh_owned(pokemon_id)
        except OwnedPokemon.DoesNotExist:
            pass

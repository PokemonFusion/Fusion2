"""Confirmed nonconsuming egg-move teaching at explicitly configured Daycare rooms."""

from collections.abc import Mapping
from contextlib import contextmanager
import hashlib
import json
from math import isfinite
from uuid import UUID, uuid4

from django.db import connection, transaction
from django.utils import timezone

from pokemon.mirror_herb import MirrorHerbRules, MirrorHerbRuleError
from pokemon.names import normalize_name, resolve_dex_entry
from pokemon.services.battle_rewards import BattleRewards
from pokemon.services.item_learning import ItemLearning, ItemLearningError
from pokemon.services.ownership import OwnershipError, assert_transferable, fresh_owned
from pokemon.services.placement import PlacementError, PlacementService


class MirrorHerbTeaching:
    """Serialize both current party targets and bind confirmation to their exact move view."""

    key = "mirror_herb_review_v1"
    review_seconds = 300

    def __init__(self, caller):
        """Use current character authority and a server-only persistent confirmation."""
        self.caller = caller
        self.learning = ItemLearning(caller)
        self.owner = self.learning.owner

    def read(self):
        """Reject malformed saved selection data without overwriting it."""
        raw = BattleRewards.stored_attribute(self.owner, self.key)
        if raw is None:
            return None
        try:
            if (not isinstance(raw, Mapping) or type(raw.get("version")) is not int or raw["version"] != 1
                    or raw.get("state") not in {"review", "done"}
                    or type(raw.get("room")) is not int or raw["room"] <= 0
                    or not isinstance(raw.get("move"), str) or not raw["move"]
                    or not isinstance(raw.get("fingerprint"), str) or len(raw["fingerprint"]) != 64
                    or any(character not in "0123456789abcdef" for character in raw["fingerprint"])
                    or any(type(raw.get(key)) not in (int, float) or not isfinite(raw[key]) or raw[key] < 0
                           for key in ("created", "expires"))
                    or raw["expires"] != raw["created"] + self.review_seconds):
                raise ValueError
            for key in ("id", "recipient", "donor"):
                UUID(str(raw[key]))
        except (KeyError, ValueError, TypeError, AttributeError) as error:
            raise OwnershipError("Your saved Mirror Herb selection needs staff review. Nothing changed.") from error
        return dict(raw)

    def token(self):
        """Capture the server-issued selection before waiting for mutation locks."""
        selection = self.read()
        return selection["id"] if selection else None

    def refresh(self):
        """Discard provisional receipt and move relation caches after either outcome."""
        from pokemon.services.item_shop import ShopPurchase

        self.owner.attributes.reset_cache()
        if connection.in_atomic_block:
            transaction.on_commit(lambda: ShopPurchase.refresh_attributes(self.owner, self.key), robust=True)
        else:
            ShopPurchase.refresh_attributes(self.owner, self.key)

    @contextmanager
    def locked(self):
        """Reuse move-learning character→storage→trainer locks before checking the current room."""
        from evennia.objects.models import ObjectDB
        from utils.locks import require_no_battle_lock

        try:
            with self.learning.locked() as (storage, trainer):
                position = ObjectDB.objects.values_list("db_location_id", flat=True).get(pk=self.owner.pk)
                room = ObjectDB.objects.filter(pk=position).first()
                if room is None or BattleRewards.stored_attribute(room, "is_daycare") is not True:
                    raise OwnershipError("Use Mirror Herb teaching at a configured Daycare.")
                if not require_no_battle_lock(self.caller):
                    raise OwnershipError("Finish your battle before teaching a move.")
                yield storage, trainer, room
        finally:
            self.refresh()

    def targets(self, storage, trainer, recipient, donor):
        """Resolve current party selectors, lock both UUIDs in order and exclude all reservations."""
        from pokemon.models.core import OwnedPokemon
        from pokemon.services.field_items import FieldMedicineUse, FieldMedicineError

        try:
            ids = [FieldMedicineUse(self.caller)._target(storage, str(query)) for query in (recipient, donor)]
            if ids[0] == ids[1]:
                raise OwnershipError("Choose two different owned party Pokemon.")
            list(OwnedPokemon.objects.select_for_update().filter(pk__in=ids).order_by("pk").values("pk"))
            result = []
            for identifier in ids:
                source, placement = PlacementService(storage)._pokemon(
                    fresh_owned(identifier), storage, operation="moves")
                assert_transferable(self.owner, source, placement)
                if source.trainer_id != trainer.pk or source.is_egg or placement.location_type != "party":
                    raise OwnershipError("Both targets must be your hatched ordinary party Pokemon.")
                result.append((source, placement))
            return result
        except (OwnedPokemon.DoesNotExist, FieldMedicineError) as error:
            raise OwnershipError("Choose two currently eligible owned party members.") from error

    def plan(self, targets, query, room):
        """Check exact native egg data, physical Herb, actual donor knowledge and one empty slot."""
        from pokemon.dex import MOVEDEX
        from pokemon.models.moves import PokemonLearnedMove, MovePPBoost

        (recipient, placement), (donor, donor_placement) = targets
        if normalize_name(recipient.held_item) != "mirrorherb":
            raise OwnershipError("The recipient must physically hold a Mirror Herb.")
        move = resolve_dex_entry(MOVEDEX, query)
        if move is None:
            raise OwnershipError("Name one complete, exact known move.")
        baby, egg = MirrorHerbRules.egg_moves(recipient.species)
        if normalize_name(move.name) not in egg:
            raise OwnershipError("That move is not in this native recipient's verified Generation 9 egg data.")
        view, _ = self.learning.view(recipient, placement)
        donor_view, _ = self.learning.view(donor, donor_placement)
        selected = [row for row in donor_view["active"] if normalize_name(row["move__name"]) == normalize_name(move.name)]
        if len(selected) != 1:
            raise OwnershipError("The donor must actually know that move in an active slot; zero PP is allowed.")
        known = list(PokemonLearnedMove.objects.filter(pokemon=recipient).order_by("move_id")
                     .values("move_id", "move__name"))
        if any(normalize_name(row["move__name"]) == normalize_name(move.name) for row in known + view["active"]):
            raise OwnershipError("The recipient already knows that move. Use the normal moveset route; PP was preserved.")
        if MovePPBoost.objects.filter(pokemon=recipient, move_id=selected[0]["move_id"]).exists():
            raise OwnershipError("Saved PP data for that new move needs staff review; nothing changed.")
        occupied = {row["slot"] for row in view["active"]}
        slot = next((number for number in range(1, 5) if number not in occupied), None)
        if slot is None or not recipient.active_moveset_id:
            raise OwnershipError("The recipient needs an empty active slot in a valid saved moveset.")
        pp = move.raw.get("pp")
        if type(pp) is not int or pp <= 0:
            raise OwnershipError("New-move PP metadata needs staff review.")
        state = {"room": room.pk, "recipient": view, "donor": donor_view,
                 "held": recipient.held_item, "donor_held": donor.held_item,
                 "knowledge": known, "egg_species": baby, "egg_moves": sorted(egg),
                 "move": move.name, "move_id": selected[0]["move_id"], "slot": slot, "pp": pp}
        fingerprint = hashlib.sha256(json.dumps(state, sort_keys=True, default=str).encode()).hexdigest()
        return state, fingerprint

    def review(self, recipient, donor, move):
        """Save only a five-minute review; it never spends an item, money, PP or a move slot."""
        with self.locked() as (storage, trainer, room):
            self.read()
            targets = self.targets(storage, trainer, recipient, donor)
            plan, fingerprint = self.plan(targets, move, room)
            now = timezone.now().timestamp()
            selection = {"version": 1, "state": "review", "id": str(uuid4()),
                "recipient": str(targets[0][0].pk), "donor": str(targets[1][0].pk),
                "room": room.pk, "move": plan["move"], "fingerprint": fingerprint,
                "created": now, "expires": now + self.review_seconds}
            self.owner.attributes.add(self.key, selection)
            message = (f"Review: teach {plan['move']} to {targets[0][0].name} from {targets[1][0].name}, "
                f"empty slot {plan['slot']}, {plan['pp']} initial PP. Native egg species: {plan['egg_species']}. "
                "No fee, egg, timer or Herb consumption. Existing moves and PP stay unchanged. "
                "Use +daycare herb confirm within five minutes, or +daycare herb cancel.")
            return {"changed": False, "message": message}

    def confirm(self, *, expected=None):
        """Recheck the exact current view, then save one knowledge/active/saved-set entry atomically."""
        from pokemon.models.moves import PokemonLearnedMove, ActiveMoveslot, MovesetSlot
        from pokemon.services.move_edits import MoveEdits

        expected = self.token() if expected is None else expected
        touched = []
        try:
            with self.locked() as (storage, trainer, room):
                selection = self.read()
                if selection is None or selection["id"] != expected:
                    raise OwnershipError("That Mirror Herb selection is no longer current. Make a fresh review.")
                if selection["state"] == "done":
                    return {"changed": False, "message": "That teaching was already saved; no move or PP was repeated."}
                now = timezone.now().timestamp()
                if not selection["created"] <= now <= selection["expires"] or room.pk != selection["room"]:
                    raise OwnershipError("That review expired or its Daycare changed. Make a fresh review.")
                targets = self.targets(storage, trainer, selection["recipient"], selection["donor"])
                touched = [source.pk for source, _ in targets]
                plan, fingerprint = self.plan(targets, selection["move"], room)
                if fingerprint != selection["fingerprint"]:
                    raise OwnershipError("The reviewed targets, item or move slots changed. Nothing was taught; make a fresh review.")
                recipient = targets[0][0]
                PokemonLearnedMove.objects.create(pokemon=recipient, move_id=plan["move_id"])
                MovesetSlot.objects.create(moveset_id=recipient.active_moveset_id, move_id=plan["move_id"], slot=plan["slot"])
                ActiveMoveslot.objects.create(pokemon=recipient, move_id=plan["move_id"], slot=plan["slot"], current_pp=plan["pp"])
                self.owner.attributes.add(self.key, dict(selection, state="done"))
                return {"changed": True, "message": f"{recipient.name} learned {plan['move']} in slot {plan['slot']}. "
                        "The Mirror Herb, donor and existing PP were preserved; no fee."}
        finally:
            for identifier in touched:
                MoveEdits._refresh(identifier)

    def cancel(self):
        """Discard only an uncommitted review, with no item or knowledge mutation."""
        with self.learning.locked():
            selection = self.read()
            if selection and selection["state"] == "review":
                self.owner.attributes.remove(self.key)
            self.refresh()
            return {"changed": False, "message": "Mirror Herb review cancelled. No move, PP, item or money changed."}

    def notify(self, result):
        """Publish success/review text only after its containing transaction commits."""
        transaction.on_commit(lambda: self.caller.msg(result["message"]), robust=True)

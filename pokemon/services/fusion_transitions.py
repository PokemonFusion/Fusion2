"""Atomic trainer/Pokemon Fusion transitions and bounded reference inspection."""

import hashlib
import json
from types import SimpleNamespace
from uuid import UUID, uuid4

from django.db import transaction

from pokemon.services.battle_rewards import BattleRewards
from pokemon.services.ownership import assert_character_free, fresh_owned, locked_owners
from pokemon.services.placement import PlacementError, PlacementService

CATEGORY = "fusion_transitions"


class FusionError(PlacementError):
    """A rejected Fusion operation leaves the previous complete state intact."""


def reset_fusion_cache(character, *, pokemon_ids=()):
    """Discard Attribute identity/handler caches after either commit or rollback."""
    from evennia.typeclasses.attributes import Attribute
    from pokemon.models.core import OwnedPokemon

    for pk in character.db_attributes.values_list("pk", flat=True):
        cached = Attribute.get_cached_instance(pk)
        if cached is not None:
            Attribute.flush_cached_instance(cached)
    character.attributes.reset_cache()
    for identifier in pokemon_ids:
        cached = OwnedPokemon.get_cached_instance(UUID(str(identifier)))
        if cached is not None:
            for key in ("_pf2_active_fusion", "_pf2_fusion_kind", "_pf2_fusion_xp", "_pf2_fusion_level", "_cached_stats"):
                cached.__dict__.pop(key, None)


class FusionTransitions:
    """Lock fresh character, storage, trainer and every referenced owned Pokemon."""

    def __init__(self, actor):
        """Accept only the acting character, not an account-wide owner capability."""
        self.character = BattleRewards.character(actor)
        self.actor_id = self.character.pk

    @staticmethod
    def _ids(character):
        """Read saved references directly from SQL, including legacy permanent state."""
        active = BattleRewards.stored_attribute(character, "fusion_id")
        kind = BattleRewards.stored_attribute(character, "fusion_kind")
        raw = BattleRewards.stored_attribute(character, "fusion_forms") or []
        if isinstance(raw, dict):
            raw = list(raw.values())
        if isinstance(raw, (str, bytes)):
            raw = [raw]
        if not isinstance(raw, (list, tuple)):
            raise FusionError("Invalid saved Fusion form list; ask staff to inspect it.")
        def canonical(value):
            """Normalize valid UUID spelling without hiding a broken reference."""
            try:
                return str(UUID(str(value)))
            except (ValueError, TypeError):
                return str(value)
        active = canonical(active) if active else None
        forms = list(dict.fromkeys(canonical(value) for value in raw if value))
        if active and kind in (None, "permanent") and str(active) not in forms:
            forms.append(str(active))
        return str(active) if active else None, kind, forms

    def inspect(self):
        """Return references and exact custody problems without repairing anything."""
        with locked_owners((self.actor_id,)) as (characters, storages, trainers):
            return self._state(characters[self.actor_id], storages[self.actor_id], trainers[self.actor_id])

    def _state(self, character, storage, trainer):
        """Inspect malformed, missing, foreign and unreferenced reservations safely."""
        from pokemon.models.core import OwnedPokemon

        problems = []
        try:
            active, kind, forms = self._ids(character)
        except FusionError as error:
            return {"character": character.pk, "problems": [{"code": "invalid_forms", "detail": str(error)}]}
        if active and kind not in (None, "temporary", "permanent"):
            problems.append({"code": "invalid_kind", "pokemon": active})
        if not active and kind is not None:
            problems.append({"code": "inactive_kind", "detail": str(kind)})
        ids = sorted({*forms, *([active] if active else [])})
        for identifier in ids:
            try:
                pokemon_id = UUID(identifier)
            except (ValueError, TypeError):
                problems.append({"code": "malformed_reference", "pokemon": identifier})
                continue
            row = OwnedPokemon.objects.filter(pk=pokemon_id).values("trainer_id").first()
            if not row:
                problems.append({"code": "missing_reference", "pokemon": identifier})
            elif row["trainer_id"] != trainer.pk:
                problems.append({"code": "foreign_reference", "pokemon": identifier})
            else:
                location = storage.placements.filter(pokemon_id=pokemon_id).values_list("location_type", flat=True).first()
                if location == "party" and identifier == active and kind in (None, "permanent"):
                    problems.append({"code": "legacy_party_reservation", "pokemon": identifier})
                elif location != "fusion":
                    problems.append({"code": "invalid_placement", "pokemon": identifier})
        for identifier in storage.placements.filter(location_type="fusion").values_list("pokemon_id", flat=True):
            if str(identifier) not in ids:
                problems.append({"code": "unreferenced_reservation", "pokemon": str(identifier)})
        state = {"character": character.pk, "active": active, "kind": kind, "forms": forms, "problems": problems}
        state["fingerprint"] = hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()
        return state

    @staticmethod
    def _source(pokemon, placement, *, permanent, slot=None):
        """Recheck all source restrictions after acquiring the storage/Pokemon locks."""
        if placement is None or placement.location_type != "party" or (slot is not None and placement.slot != slot):
            raise FusionError("That Pokemon is no longer in the selected party slot.")
        if pokemon.is_egg:
            raise FusionError("Eggs cannot be used for fusion.")
        if str(pokemon.held_item or "").strip().lower() not in ("", "nothing"):
            raise FusionError("That Pokemon must not be holding an item before fusion.")
        if {str(flag).lower() for flag in (pokemon.flags or [])} & {"breeding", "breeding_parent", "carrying_egg"}:
            raise FusionError("That Pokemon cannot fuse while breeding or carrying an egg.")
        required = 255 if permanent else 140
        if pokemon.friendship < required:
            raise FusionError(f"Bond must be at least {required} for this fusion. Current Bond: {pokemon.friendship}.")

    def run(self, action, pokemon=None, *, slot=None, request_id=None):
        """Commit one complete transition and receipt, or retain the previous state."""
        from pokemon.models.core import OwnedPokemon
        from utils import fusion

        if action not in {"temporary", "permanent", "switch", "deactivate"}:
            raise FusionError("Unknown Fusion transition.")
        if slot is not None and (type(slot) is not int or slot not in range(1, 7)):
            raise FusionError("Choose a party slot between 1 and 6.")
        if action == "deactivate" and (pokemon is not None or slot is not None):
            raise FusionError("Unfuse uses your current saved form.")
        try:
            identifier = str(UUID(str(pokemon.pk))) if pokemon is not None else None
            request = str(UUID(str(request_id))) if request_id is not None else str(uuid4())
        except (ValueError, TypeError, AttributeError) as error:
            raise FusionError("Invalid Fusion target or request identity.") from error
        terms = {"action": action, "pokemon": identifier, "slot": slot}
        key = "fusion:" + request
        reference_ids = set()
        try:
            with locked_owners((self.actor_id,)) as (characters, storages, trainers):
                character, storage, trainer = characters[self.actor_id], storages[self.actor_id], trainers[self.actor_id]
                receipt = BattleRewards.stored_attribute(character, key, category=CATEGORY)
                if receipt is not None:
                    if receipt["terms"] != terms:
                        raise FusionError("Request identity already belongs to different Fusion terms.")
                    return receipt["success"], receipt["message"]
                assert_character_free(character)
                state = self._state(character, storage, trainer)
                if any(problem["code"] != "legacy_party_reservation" for problem in state["problems"]):
                    raise FusionError("Your saved Fusion needs staff review; no Pokemon or progress was changed.")
                for problem in state["problems"]:
                    # Legacy chargen explicitly recorded an owned permanent form
                    # but retained its party slot. Normalize only that exact role;
                    # this grants no form, EXP, item, HP or ownership change.
                    PlacementService(storage).reserve_for_fusion(fresh_owned(problem["pokemon"], lock=True))
                state = self._state(character, storage, trainer)
                reference_ids = set(state["forms"])
                if state["active"]:
                    reference_ids.add(state["active"])
                if identifier:
                    reference_ids.add(identifier)
                assets = {}
                try:
                    for pokemon_id in sorted(reference_ids):
                        mon = fresh_owned(pokemon_id, lock=True)
                        assets[pokemon_id] = PlacementService(storage)._pokemon(mon, storage)
                except OwnedPokemon.DoesNotExist as error:
                    raise FusionError("That Pokemon no longer exists.") from error
                actor = SimpleNamespace(db=character.db, storage=storage, trainer=trainer, character=character)
                if action in {"temporary", "permanent", "switch"} and identifier is None:
                    raise FusionError("Choose one of your owned Pokemon.")
                source, placement = assets.get(identifier, (None, None))
                if action == "temporary":
                    if state["active"] == identifier and state["kind"] == "temporary":
                        result = (True, f"You are already temporarily fused with {fusion._display_name(source)}.")
                    else:
                        self._source(source, placement, permanent=False, slot=slot)
                        result = fusion._legacy_activate_temporary_fusion(actor, source, slot=placement.slot)
                elif action in {"permanent", "switch"}:
                    if identifier in state["forms"]:
                        result = fusion._legacy_activate_permanent_form(actor, source)
                    elif action == "switch":
                        raise FusionError("That permanent Fusion form has not been unlocked.")
                    else:
                        self._source(source, placement, permanent=True, slot=slot)
                        result = fusion._legacy_activate_permanent_fusion(actor, source)
                else:
                    result = fusion._legacy_deactivate_fusion(actor)
                if not result[0]:
                    raise FusionError(result[1])
                if self._state(character, storage, trainer)["problems"]:
                    raise FusionError("Fusion did not reach a valid saved state; your previous state was retained.")
                character.attributes.add(key, {"terms": terms, "success": result[0], "message": result[1]}, category=CATEGORY)
                transaction.on_commit(lambda: reset_fusion_cache(character, pokemon_ids=reference_ids))
                return result
        finally:
            reset_fusion_cache(self.character, pokemon_ids=reference_ids)

    def clear_invalid_references(self, expected_fingerprint, *, operator_note):
        """Staff-only primitive: remove reviewed missing/foreign references, no assets.

        The operator-facing command must enforce staff permissions. Invalid owned
        placement or an orphan reservation requires a separate explicit decision;
        this route cannot guess which form/party state the player intended.
        """
        from utils import fusion

        if not operator_note or not operator_note.strip():
            raise FusionError("Record an operator note for this recovery.")
        try:
            with locked_owners((self.actor_id,)) as (characters, storages, trainers):
                character = characters[self.actor_id]
                assert_character_free(character)
                state = self._state(character, storages[self.actor_id], trainers[self.actor_id])
                if state.get("fingerprint") != expected_fingerprint:
                    raise FusionError("Fusion state changed; inspect it again before recovery.")
                safe = {"missing_reference", "foreign_reference", "malformed_reference"}
                if not state["problems"] or any(problem["code"] not in safe for problem in state["problems"]):
                    raise FusionError("This state needs deliberate custody review; no automatic repair is safe.")
                invalid = {problem["pokemon"] for problem in state["problems"]}
                character.attributes.add("fusion_forms", [pid for pid in state["forms"] if pid not in invalid])
                if state["active"] in invalid:
                    fusion._clear_character_fusion_view(character)
                character.attributes.add("recovery:" + str(uuid4()),
                    {"before": state, "operator_note": operator_note.strip()}, category=CATEGORY)
                transaction.on_commit(lambda: reset_fusion_cache(character))
                return self._state(character, storages[self.actor_id], trainers[self.actor_id])
        finally:
            reset_fusion_cache(self.character)

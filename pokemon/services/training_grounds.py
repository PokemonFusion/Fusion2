"""Persistent, deliberate field training and confirmed EV retraining."""

from collections.abc import Mapping, MutableSequence
from contextlib import contextmanager
from copy import copy
from datetime import datetime
from math import isfinite
from types import SimpleNamespace
from uuid import UUID, uuid4

from django.db import transaction
from django.utils import timezone

from pokemon.hyper_training import HyperTraining
from pokemon.services.battle_rewards import BattleRewards
from pokemon.services.field_items import FieldMedicineError, FieldMedicineUse
from pokemon.services.field_progression import FieldProgressionUse
from pokemon.services.placement import PlacementError, PlacementService


class TrainingError(ValueError):
    """A training request cannot change the current saved state."""


class TrainingGrounds:
    """Serialize current room, character, placement, target and session receipts."""

    key = "training_grounds_v1"
    gain = 64
    step_seconds = 30
    steps = 3
    review_seconds = 300
    approaches = frozenset({"technique", "pace", "recovery"})
    stats = HyperTraining.stats

    def __init__(self, caller, *, clock=None):
        """Only server code supplies the clock; player inputs carry no progress."""
        self.caller = caller
        self.clock = clock or timezone.now

    def _now(self):
        """Reject invalid/naive clocks instead of manufacturing elapsed progress."""
        value = self.clock()
        if (not isinstance(value, datetime) or not timezone.is_aware(value)
                or not isfinite(value.timestamp()) or value.timestamp() < 0):
            raise TrainingError("The training clock is unavailable. Nothing changed.")
        return value.timestamp()

    @staticmethod
    def _evs(values):
        """Validate a saved EV vector without coercing malformed data."""
        from django.core.exceptions import ValidationError
        from pokemon.models.validators import validate_evs

        if not isinstance(values, (list, tuple, MutableSequence)) or len(values) != 6:
            raise TrainingError("Invalid saved EVs; contact staff. Nothing changed.")
        result = list(values)
        if any(type(value) is not int for value in result):
            raise TrainingError("Invalid saved EVs; contact staff. Nothing changed.")
        try:
            validate_evs(result)
        except ValidationError as error:
            raise TrainingError("Invalid saved EVs; contact staff. Nothing changed.") from error
        return result

    @classmethod
    def _profile(cls, owner):
        """Copy only a valid receipt schema, including Evennia saved containers."""
        raw = BattleRewards.stored_attribute(owner, cls.key)
        if raw is None:
            return {"version": 1, "completed": 0, "gold_awarded": False, "pending": None, "last": None}
        if (not isinstance(raw, Mapping) or type(raw.get("version")) is not int or raw.get("version") != 1
                or type(raw.get("completed")) is not int or not 0 <= raw["completed"] < 2 ** 31
                or type(raw.get("gold_awarded")) is not bool
                or raw["gold_awarded"] != (raw["completed"] >= 60)):
            raise TrainingError("Your training record needs staff review. Nothing changed.")
        result = dict(raw)
        pending = raw.get("pending")
        if pending is not None:
            if (not isinstance(pending, Mapping)
                    or pending.get("kind") not in {"session_review", "session", "reset_review"}
                    or pending.get("stat") not in (*cls.stats, "all")
                    or type(pending.get("level")) is not int or not 1 <= pending["level"] <= 100
                    or type(pending.get("room")) is not int or pending["room"] <= 0
                    or type(pending.get("amount")) is not int or not 0 <= pending["amount"] <= 510
                    or not isinstance(pending.get("placement"), (list, tuple, MutableSequence))
                    or len(pending["placement"]) != 2):
                raise TrainingError("Your pending training record needs staff review. Nothing changed.")
            for key in ("id", "target"):
                try:
                    UUID(str(pending.get(key)))
                except (ValueError, TypeError, AttributeError) as error:
                    raise TrainingError("Your pending training record needs staff review. Nothing changed.") from error
            for key in ("created_at", "expires_at"):
                if (type(pending.get(key)) not in (int, float)
                        or not isfinite(pending[key]) or pending[key] < 0):
                    raise TrainingError("Your training clock record needs staff review. Nothing changed.")
            result["pending"] = dict(pending, baseline=cls._evs(pending.get("baseline")),
                                     placement=list(pending["placement"]))
            if (not isinstance(pending.get("preview_stats"), Mapping)
                    or set(pending["preview_stats"]) != set(cls.stats)
                    or any(type(value) is not int or value < 0 for value in pending["preview_stats"].values())
                    or type(pending.get("preview_hp")) is not int or pending["preview_hp"] < 0):
                raise TrainingError("Your stat review needs staff review. Nothing changed.")
            result["pending"]["preview_stats"] = dict(pending["preview_stats"])
            baseline = result["pending"]["baseline"]
            place, slot = pending["placement"]
            if (place not in {"party", "fusion"}
                    or (place == "party" and (type(slot) is not int or slot not in range(1, 7)))
                    or (place == "fusion" and slot is not None)
                    or pending["preview_hp"] > pending["preview_stats"]["hp"]
                    or pending["amount"] <= 0):
                raise TrainingError("Your training selection needs staff review. Nothing changed.")
            if pending["kind"] == "reset_review":
                capacity = sum(baseline) if pending["stat"] == "all" else baseline[cls.stats.index(pending["stat"])]
                if pending["amount"] > capacity or (pending["stat"] == "all" and pending["amount"] != capacity):
                    raise TrainingError("Your reset selection needs staff review. Nothing changed.")
            elif (pending["stat"] == "all" or pending["amount"] != min(
                    cls.gain, 252 - baseline[cls.stats.index(pending["stat"])], 510 - sum(baseline))):
                raise TrainingError("Your exercise selection needs staff review. Nothing changed.")
            if pending["kind"] == "session":
                if (type(pending.get("step")) is not int or not 0 <= pending["step"] < cls.steps
                        or type(pending.get("next_at")) not in (int, float)
                        or not isfinite(pending["next_at"])
                        or pending["next_at"] < pending["created_at"] + (pending["step"] + 1) * cls.step_seconds
                        or pending["stat"] == "all"):
                    raise TrainingError("Your exercise record needs staff review. Nothing changed.")
        last = raw.get("last")
        if last is not None and not isinstance(last, Mapping):
            raise TrainingError("Your training receipt needs staff review. Nothing changed.")
        result["last"] = dict(last) if last is not None else None
        return result

    def token(self):
        """Capture the expected internal session/step before waiting for write locks."""
        from evennia.objects.models import ObjectDB

        owner = ObjectDB.objects.get(pk=self.caller.pk)
        pending = self._profile(owner)["pending"]
        return (pending["id"], pending.get("step")) if pending else (None, None)

    @contextmanager
    def locked(self, *, require_ground=True):
        """Use the same room→owner→storage→trainer order as durable field activities."""
        from evennia.objects.models import ObjectDB
        from pokemon.models.storage import UserStorage
        from pokemon.models.trainer import Trainer

        owner, touched = None, []
        try:
            with transaction.atomic():
                room_id = ObjectDB.objects.values_list("db_location_id", flat=True).get(pk=self.caller.pk)
                room = ObjectDB.objects.select_for_update().filter(pk=room_id).first() if require_ground else None
                owner_row = ObjectDB.objects.select_for_update().values("pk", "db_location_id").get(pk=self.caller.pk)
                owner = ObjectDB.objects.get(pk=owner_row["pk"])
                if require_ground and (room is None or owner_row["db_location_id"] != room.pk
                                       or BattleRewards.stored_attribute(room, "training_ground") is not True):
                    raise TrainingError("Use this activity at the Training Grounds.")
                storage = UserStorage.objects.select_for_update().get(user_id=owner.pk)
                trainer = Trainer.objects.select_for_update().get(user_id=owner.pk)
                owner.attributes.reset_cache()
                yield SimpleNamespace(owner=owner, room=room, storage=storage, trainer=trainer,
                                      profile=self._profile(owner), now=self._now(), touched=touched)
        except (ObjectDB.DoesNotExist, UserStorage.DoesNotExist, Trainer.DoesNotExist) as error:
            raise TrainingError("Your current trainer or location is unavailable. Nothing changed.") from error
        finally:
            if owner is not None:
                owner.attributes.reset_cache()
            for pokemon in touched:
                FieldProgressionUse(self.caller)._resync(pokemon)

    def _owned(self, context, query, *, living):
        """Re-resolve actual custody and battle state under the activity locks."""
        from pokemon.models.core import OwnedPokemon
        from pokemon.helpers.pokemon_helpers import get_max_hp
        from utils.locks import _has_active_battle_ref

        if (any(_has_active_battle_ref(BattleRewards.stored_attribute(context.owner, key))
                for key in ("battle_lock", "battle_id"))
                or getattr(self.caller.ndb, "battle_instance", None)):
            raise TrainingError("Finish your battle before training or retraining.")
        try:
            identifier = FieldMedicineUse(self.caller)._target(context.storage, str(query))
            row = OwnedPokemon.objects.select_for_update().values().get(pk=identifier)
            original = OwnedPokemon.objects.get(pk=identifier)
            FieldMedicineUse._refresh(original, row)
            context.touched.append(original)
            pokemon, placement = PlacementService(context.storage)._pokemon(
                original, context.storage, operation="field")
            pokemon = copy(pokemon)
            pokemon._state = copy(pokemon._state)
            if (pokemon.trainer_id != context.trainer.pk or pokemon.is_egg or placement is None
                    or placement.location_type not in {"party", "fusion"}):
                raise TrainingError("Choose an eligible owned party member or your current Fusion.")
            self._evs(pokemon.evs)
            if (type(pokemon.level) is not int or not 1 <= pokemon.level <= 100
                    or type(pokemon.current_hp) is not int
                    or not 0 <= pokemon.current_hp <= get_max_hp(pokemon)):
                raise TrainingError("Invalid saved level or HP; contact staff. Nothing changed.")
            if living and pokemon.current_hp <= 0:
                raise TrainingError("A fainted Pokemon cannot complete a training exercise.")
            return pokemon, placement
        except (OwnedPokemon.DoesNotExist, FieldMedicineError, PlacementError) as error:
            raise TrainingError(str(error) or "That target is no longer eligible.") from error

    @staticmethod
    def _save(context):
        """Replace a detached receipt, never mutate an autosaving nested container."""
        context.owner.attributes.add(TrainingGrounds.key, context.profile)

    @staticmethod
    def _snapshot(pokemon, placement):
        """Bind destructive confirmation to actual training state and canonical placement."""
        return {"target": str(pokemon.pk), "baseline": list(pokemon.evs), "level": pokemon.level,
                "placement": [placement.location_type, placement.slot]}

    def _pending(self, context, expected, *, kinds):
        """Refuse outdated reviews/steps without replaying effects or erasing new state."""
        pending = context.profile["pending"]
        if pending is None or pending["id"] != expected[0] or pending["kind"] not in kinds:
            raise TrainingError("That training selection is no longer current. Inspect +train first.")
        if context.now < pending["created_at"]:
            raise TrainingError("The server clock moved backwards. Nothing changed.")
        if pending["kind"] != "session" and context.now > pending["expires_at"]:
            raise TrainingError("That review expired. Make a fresh selection; nothing changed.")
        if pending["room"] != context.room.pk:
            raise TrainingError("Return to the Training Grounds where you selected this activity.")
        pokemon, placement = self._owned(context, pending["target"], living=pending["kind"] != "reset_review")
        if any(self._snapshot(pokemon, placement)[key] != pending[key]
               for key in ("target", "baseline", "level", "placement")):
            raise TrainingError("That Pokemon's training or placement changed. Cancel and make a fresh selection.")
        if pending["kind"] == "reset_review":
            from pokemon.helpers.pokemon_helpers import get_stats

            if (pokemon.current_hp != pending["preview_hp"]
                    or get_stats(pokemon) != pending["preview_stats"]):
                raise TrainingError("The reviewed stats or HP changed. Cancel and make a fresh reset preview.")
        return pending, pokemon

    @staticmethod
    def _change(pokemon, evs):
        """Persist validated EVs and the ordinary max-HP deficit adjustment only."""
        from pokemon.helpers.pokemon_helpers import get_max_hp, refresh_stats

        old_max, hp = get_max_hp(pokemon), pokemon.current_hp
        pokemon.evs = list(evs)
        pokemon.__dict__.pop("_cached_stats", None)
        maximum = refresh_stats(pokemon)["hp"]
        pokemon.current_hp = 0 if hp <= 0 else max(1, min(maximum, hp + maximum - old_max))
        pokemon.save(update_fields=["evs", "current_hp"])

    def review(self, target, stat, *, reset=False, amount=None):
        """Preview a useful exact change, leaving every Pokemon resource untouched."""
        from pokemon.helpers.pokemon_helpers import get_stats

        stat = "all" if reset and str(stat).casefold() == "all" else HyperTraining.stat(stat)
        if stat is None or (not reset and stat == "all"):
            raise TrainingError("Choose HP, Attack, Defense, SpA, SpD or Speed; reset also accepts all.")
        if amount is not None and (not reset or stat == "all" or type(amount) is not int or not 1 <= amount <= 252):
            raise TrainingError("A partial reset needs one stat and an amount from 1 through 252.")
        with self.locked() as context:
            if context.profile["pending"] and context.profile["pending"]["kind"] == "session":
                raise TrainingError("Cancel your active training session before choosing another activity.")
            pokemon, placement = self._owned(context, target, living=not reset)
            evs = list(pokemon.evs)
            if reset:
                if stat == "all":
                    change, result = sum(evs), [0] * 6
                else:
                    index = self.stats.index(stat)
                    change = evs[index] if amount is None else amount
                    if change > evs[index]:
                        raise TrainingError("That stat has fewer EVs than the requested reset amount.")
                    result = list(evs)
                    result[index] -= change
            else:
                index = self.stats.index(stat)
                change = min(self.gain, 252 - evs[index], 510 - sum(evs))
                result = list(evs)
                result[index] += change
            if change <= 0:
                raise TrainingError("That activity has no useful EV effect. Nothing changed.")
            before = get_stats(pokemon)
            preview = copy(pokemon)
            preview.evs = result
            preview.__dict__.pop("_cached_stats", None)
            after = get_stats(preview)
            pending = dict(self._snapshot(pokemon, placement), id=str(uuid4()),
                           kind="reset_review" if reset else "session_review", stat=stat,
                           amount=change, room=context.room.pk, created_at=context.now,
                           expires_at=context.now + self.review_seconds,
                           preview_stats=before, preview_hp=pokemon.current_hp)
            after_hp = (0 if pokemon.current_hp <= 0 else
                        max(1, min(after["hp"], pokemon.current_hp + after["hp"] - before["hp"])))
            context.profile["pending"] = pending
            self._save(context)
            return {"changed": True, "kind": pending["kind"], "id": pending["id"], "target": str(pokemon.pk),
                    "before_evs": evs, "after_evs": result, "before_stats": before, "after_stats": after,
                    "before_hp": pokemon.current_hp, "after_hp": after_hp,
                    "cost": 0, "message": f"Review {pokemon.name}: {evs} → {result}; stats {before} → {after}. "
                    + f"HP {pokemon.current_hp}/{before['hp']} → {after_hp}/{after['hp']}. "
                    + ("Reset is free and gives no rewards. " if reset else "Three active 30-second steps; no EXP or fee. ")
                    + "Use +train confirm within five minutes, or +train cancel."}

    def confirm(self, *, expected=None):
        """Start once or commit one reset; a repeated confirmation never refreshes a timer."""
        expected = self.token() if expected is None else expected
        with self.locked() as context:
            pending = context.profile["pending"]
            if pending and pending["id"] == expected[0] and pending["kind"] == "session":
                return {"changed": False, "message": "That session is already started. Use +train status."}
            if pending is None and context.profile["last"]:
                return {"changed": False, "message": "Your previous activity is already saved; no effect was repeated."}
            pending, pokemon = self._pending(context, expected, kinds={"session_review", "reset_review"})
            if pending["kind"] == "session_review":
                context.profile["pending"] = dict(pending, kind="session", step=0,
                                                  created_at=context.now, next_at=context.now + self.step_seconds)
                self._save(context)
                return {"changed": True, "message": "Training started. First exercise in 30 seconds. "
                        "Use +train continue technique, pace or recovery; +train status shows progress."}
            evs = list(pokemon.evs)
            if pending["stat"] == "all":
                evs = [0] * 6
            else:
                evs[self.stats.index(pending["stat"])] -= pending["amount"]
            self._change(pokemon, evs)
            context.profile["last"] = {"id": pending["id"], "kind": "reset", "target": str(pokemon.pk),
                                       "evs": evs, "completed_at": context.now}
            context.profile["pending"] = None
            self._save(context)
            return {"changed": True, "message": f"Retraining saved: {pokemon.name} EVs {evs}. No fee or reward."}

    def advance(self, approach, *, expected=None):
        """One deliberate current step; only the third credits the frozen useful gain."""
        if approach not in self.approaches:
            raise TrainingError("Choose technique, pace or recovery; each trains the selected stat equally.")
        expected = self.token() if expected is None else expected
        with self.locked() as context:
            pending, pokemon = self._pending(context, expected, kinds={"session"})
            if pending["step"] != expected[1]:
                raise TrainingError("That exercise step was already handled. Inspect +train status.")
            if context.now < pending["next_at"]:
                wait = max(1, int(pending["next_at"] - context.now + 0.999))
                raise TrainingError(f"Your next exercise opens in{wait} seconds. No progress was credited.")
            step = pending["step"] + 1
            if step < self.steps:
                context.profile["pending"] = dict(pending, step=step, next_at=context.now + self.step_seconds)
                self._save(context)
                return {"changed": True, "message": f"Exercise {step}/3 complete ({approach}). Next in 30 seconds."}
            evs = list(pokemon.evs)
            index = self.stats.index(pending["stat"])
            gain = min(pending["amount"], 252 - evs[index], 510 - sum(evs))
            if gain <= 0:
                raise TrainingError("There is no useful training capacity. Cancel and choose another stat.")
            evs[index] += gain
            self._change(pokemon, evs)
            completed = context.profile["completed"] + 1
            rewards = []
            if completed % 6 == 0:
                rewards.append("Rare Candy")
            if completed % 12 == 0:
                rewards.append("Bottle Cap")
            if completed == 60:
                rewards.append("Gold Bottle Cap")
            for item in rewards:
                if context.trainer.add_item(item, 1) is False:
                    raise TrainingError("The earned reward could not be saved. No training was committed.")
            context.profile.update(completed=completed, gold_awarded=completed >= 60, pending=None,
                                   last={"id": pending["id"], "kind": "session", "target": str(pokemon.pk),
                                         "stat": pending["stat"], "gain": gain, "evs": evs,
                                         "rewards": rewards, "completed_at": context.now})
            self._save(context)
            suffix = "; earned " + ", ".join(rewards) if rewards else ""
            return {"changed": True, "gain": gain, "rewards": rewards,
                    "message": f"Training saved: {pokemon.name} +{gain} {pending['stat']} EVs; "
                    f"{evs[index]}/252 in that stat, {sum(evs)}/510 total. Useful sessions: {completed}{suffix}."}

    def status(self):
        """Inspect saved progress anywhere, including after reconnect or interruption."""
        with self.locked(require_ground=False) as context:
            pending = context.profile["pending"]
            result = {"completed": context.profile["completed"], "pending": pending,
                      "message": f"Useful training sessions: {context.profile['completed']}. "}
            if not pending:
                result["message"] += "No active activity. At Training Grounds use +train <target>=<stat>."
            elif pending["kind"] == "session":
                wait = max(0, int(pending["next_at"] - context.now + 0.999))
                result["message"] += f"{pending['stat']}: exercise {pending['step']}/3; next in{wait}s. "
                result["message"] += "Use +train continue technique, pace or recovery; cancel is free."
            else:
                result["message"] += "A selection awaits +train confirm; +train cancel discards it."
            return result

    def cancel(self):
        """Discard only this owner's current selection, with no cost or reward."""
        with self.locked(require_ground=False) as context:
            changed = context.profile["pending"] is not None
            context.profile["pending"] = None
            self._save(context)
            return {"changed": changed, "message": "Training selection cancelled. No EVs, costs or rewards changed."}

    def notify(self, result):
        """Report a committed result only after the outermost transaction succeeds."""
        transaction.on_commit(lambda: self.caller.msg(result["message"]), robust=True)

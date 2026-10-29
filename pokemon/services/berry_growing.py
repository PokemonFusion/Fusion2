"""Fresh owner/access guards and atomic, cycle-bound reviewed berry growing."""

from contextlib import contextmanager
from datetime import timedelta
from uuid import uuid4

from django.db import transaction
from django.utils import timezone

from pokemon.services.battle_rewards import BattleRewards


class BerryGrowingError(ValueError):
    """A rejected garden request changes no crop or inventory."""


class BerryGrowing:
    """Lock room, character, storage, trainer, then bed; never credit from timers."""

    stage_seconds = 3600
    growing_seconds = 14400
    seeds = ("Oran Berry", "Cheri Berry", "Pecha Berry", "Rawst Berry", "Aspear Berry",
             "Chesto Berry", "Sitrus Berry", "Lum Berry")

    @classmethod
    def canonical_seed(cls, name):
        """Bind only the eight explicitly reviewed names before mutation locks."""
        from pokemon.names import normalize_name

        if not isinstance(name, str):
            raise BerryGrowingError("Choose one accepted bag berry seed; see +berry help.")
        matches = [seed for seed in cls.seeds if normalize_name(seed) == normalize_name(name)]
        if len(matches) != 1:
            raise BerryGrowingError("Choose one accepted bag berry seed; see +berry help.")
        return matches[0]

    def __init__(self, caller, *, clock=None):
        """Keep a server-owned clock injectable only by controlled tests."""
        self.caller = caller
        self.clock = clock or timezone.now

    def cycle(self):
        """Capture a request's identity before it can wait for any mutation locks."""
        from pokemon.models.berries import BerryBed

        return BerryBed.objects.filter(trainer__user_id=self.caller.pk).values_list("cycle_id", flat=True).first()

    @contextmanager
    def locked(self):
        """Read SQL source/owner state instead of stale location or Attribute caches."""
        from evennia.objects.models import ObjectDB
        from pokemon.models.berries import BerryBed
        from pokemon.models.storage import UserStorage
        from pokemon.models.trainer import Trainer
        from utils.locks import _has_active_battle_ref

        with transaction.atomic():
            room_id = ObjectDB.objects.filter(pk=self.caller.pk).values_list("db_location_id", flat=True).first()
            room = ObjectDB.objects.select_for_update().filter(pk=room_id).first()
            if room is None or BattleRewards.stored_attribute(room, "berry_nursery") is not True:
                raise BerryGrowingError("Use the growing commands at a Berry Nursery.")
            owner_row = ObjectDB.objects.select_for_update().filter(pk=self.caller.pk).values("pk", "db_location_id").get()
            owner = ObjectDB.objects.get(pk=owner_row["pk"])
            if owner_row["db_location_id"] != room_id:
                raise BerryGrowingError("Your location changed; try again at the nursery.")
            if (any(_has_active_battle_ref(BattleRewards.stored_attribute(owner, key))
                    for key in ("battle_lock", "battle_id"))
                    or getattr(self.caller.ndb, "battle_instance", None)):
                raise BerryGrowingError("Finish your battle before tending berries.")
            storage = UserStorage.objects.select_for_update().filter(user_id=owner.pk).first()
            trainer = Trainer.objects.select_for_update().filter(user_id=owner.pk).first()
            if storage is None or trainer is None:
                raise BerryGrowingError("You need your own trainer and storage to grow berries.")
            bed = BerryBed.objects.select_for_update().filter(trainer_id=trainer.pk).first()
            yield trainer, bed

    def state(self, bed, *, now=None):
        """Derive elapsed growth from validated saved UTC times, including offline time."""
        now = self.clock() if now is None else now
        if not timezone.is_aware(now) or now.timestamp() < 0:
            raise BerryGrowingError("Invalid server clock; no crop was changed.")
        if bed is None or bed.cycle_id is None:
            if bed and (bed.berry or bed.planted_at or bed.ready_at or bed.watered_mask):
                raise BerryGrowingError("Invalid saved empty bed; contact staff.")
            return {"cycle": None, "berry": "", "stage": None, "ready": False,
                    "last_harvest_cycle": str(bed.last_harvest_cycle) if bed and bed.last_harvest_cycle else None}
        if (bed.berry not in self.seeds or not bed.planted_at or not bed.ready_at
                or not timezone.is_aware(bed.planted_at) or not timezone.is_aware(bed.ready_at)
                or bed.planted_at > now or bed.planted_at.timestamp() < 0
                or bed.ready_at != bed.planted_at + timedelta(seconds=self.growing_seconds)
                or not 0 <= bed.watered_mask <= 15):
            raise BerryGrowingError("Invalid saved growing cycle or server clock; contact staff.")
        elapsed = (now - bed.planted_at).total_seconds()
        stage = min(4, int(elapsed // self.stage_seconds))
        return {"cycle": str(bed.cycle_id), "berry": bed.berry, "stage": stage, "ready": stage == 4,
                "ready_at": bed.ready_at.isoformat(), "watered_mask": bed.watered_mask,
                "yield": 1 + bed.watered_mask.bit_count()}

    def status(self):
        """Read one owner's bed at an authorized nursery without creating inventory."""
        with self.locked() as (_, bed):
            return self.state(bed)

    def operate(self, action, *, cycle, seed=None):
        """Bind even concurrent/replayed requests to the cycle originally observed."""
        from pokemon.models.berries import BerryBed

        if action not in {"plant", "water", "harvest"}:
            raise BerryGrowingError("Unknown growing action.")
        if seed is not None and action != "plant":
            raise BerryGrowingError("Only planting accepts a seed name; inspect the current crop.")
        canonical = self.canonical_seed(seed if seed is not None else "Oran Berry") if action == "plant" else None
        with self.locked() as (trainer, bed):
            now = self.clock()
            state = self.state(bed, now=now)
            expected = str(cycle) if cycle else None
            if expected != state["cycle"]:
                if action == "harvest" and state["cycle"] is None and expected == state["last_harvest_cycle"]:
                    return {"changed": False, "message": "That crop was already harvested. Nothing was credited."}
                raise BerryGrowingError("That growing request is stale; inspect your current bed and try again.")
            if action == "plant":
                if state["cycle"] is not None:
                    raise BerryGrowingError("Your bed already has a growing crop.")
                if not trainer.remove_item(canonical):
                    raise BerryGrowingError(f"You need one bag {canonical} to plant; held copies are not seeds.")
                bed = bed or BerryBed(trainer=trainer)
                bed.cycle_id, bed.berry = uuid4(), canonical
                bed.planted_at, bed.ready_at = now, now + timedelta(seconds=self.growing_seconds)
                bed.watered_mask = 0
                bed.save()
                message = f"Planted one {canonical}. Ready at {bed.ready_at.isoformat()} (four hours)."
            elif action == "water":
                if not state["cycle"]:
                    raise BerryGrowingError("Your bed is empty; plant an accepted bag berry first.")
                if state["ready"]:
                    raise BerryGrowingError("Your crop is ready to harvest; it cannot be watered now.")
                bit = 1 << state["stage"]
                if bed.watered_mask & bit:
                    return {"changed": False, "message": "This stage is already watered. Nothing changed."}
                bed.watered_mask |= bit
                bed.save(update_fields=["watered_mask"])
                message = f"Watered growing stage {state['stage'] + 1}. Expected yield: {1 + bed.watered_mask.bit_count()}."
            else:
                if not state["cycle"]:
                    return {"changed": False, "message": "Your bed is empty; any previous crop is already claimed."}
                if not state["ready"]:
                    raise BerryGrowingError(f"Your crop is not ready until {state['ready_at']}.")
                quantity = state["yield"]
                harvested = bed.berry
                trainer.add_item(harvested, quantity)
                bed.last_harvest_cycle, bed.last_harvest_yield = bed.cycle_id, quantity
                bed.cycle_id, bed.berry = None, ""
                bed.planted_at, bed.ready_at, bed.watered_mask = None, None, 0
                bed.save()
                message = f"Harvested {quantity} {harvested}. Your bed is empty; replant explicitly."
            result = {"changed": True, "message": message, "state": self.state(bed, now=now)}
            transaction.on_commit(lambda: self.caller.msg(message), robust=True)
            return result

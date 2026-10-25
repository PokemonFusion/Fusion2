"""Four new seeds through real commands and controlled-clock disposable SQL.

These fixtures never claim the four-real-hour released acceptance in #893.
"""

from datetime import timedelta
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import item_availability_cases as acquisition
import berry_growing_cases as legacy

EVIDENCE = legacy.EVIDENCE
SEEDS = {"Cheri Berry": "par", "Pecha Berry": "tox", "Rawst Berry": "brn", "Aspear Berry": "frz"}


class SeedGrowingCases(unittest.TestCase):
    """Reuse the guarded owner/transport fixture with four real new bag seeds."""

    native = legacy.BerryGrowingCases.native
    command = legacy.BerryGrowingCases.command
    reply = legacy.BerryGrowingCases.reply
    tearDown = legacy.BerryGrowingCases.tearDown
    growing = legacy.BerryGrowingCases.growing
    state = legacy.BerryGrowingCases.state
    record = legacy.BerryGrowingCases.record
    buy = legacy.BerryGrowingCases.buy
    race = legacy.BerryGrowingCases.race

    def setUp(self):
        """Keep old nursery stock independent; author only this suite's new offers."""
        legacy.BerryGrowingCases.setUp(self)
        self.room.db.store_inventory = {name: {"price": 100, "quantity": 5} for name in SEEDS}

    def plant(self):
        """Purchase and plant exactly the selected current seed through ordinary input."""
        self.buy(self.seed)
        self.record("plant " + self.seed)
        self.assertEqual(self.player.trainer.get_item_quantity(self.seed), 0)
        self.assertEqual(self.state()["bed"]["berry"], self.seed)
        return self.growing().cycle()

    def masks(self, mask):
        """Each watering mask harvests exactly the saved berry once, then cures status."""
        cycle, planted = self.plant(), self.now
        for stage in range(4):
            self.now = planted + timedelta(hours=stage)
            if mask & (1 << stage):
                self.record("water")
                before = self.state()
                self.record("water")
                self.assertEqual(self.state(), before)
        self.now = planted + timedelta(hours=4)
        self.assertEqual(self.growing().status()["berry"], self.seed)
        self.record("status")
        self.assertIn(self.seed, self.player.messages[-1])
        self.record("harvest")
        quantity = 1 + mask.bit_count()
        self.assertEqual(self.player.trainer.get_item_quantity(self.seed), quantity)
        self.assertEqual(self.state()["bed"]["last_harvest_cycle"], cycle)
        before = self.state()
        self.growing().operate("harvest", cycle=cycle)
        self.record("harvest")
        self.assertEqual(self.state(), before)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(status=SEEDS[self.seed])
        self.command("use", self.seed + "=3")
        self.assertEqual(
            OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("status", flat=True).get(), ""
        )
        self.assertEqual(self.player.trainer.get_item_quantity(self.seed), quantity - 1)

    def stale(self):
        """An old request cannot water, harvest or change a replacement berry family."""
        old = self.plant()
        self.now += timedelta(hours=4)
        self.record("harvest")
        other = next(seed for seed in SEEDS if seed != self.seed)
        self.buy(other)
        self.record("plant " + other)
        self.now += timedelta(hours=4)
        before = self.state()
        for action in ("water", "harvest", "plant"):
            with self.assertRaises(BerryGrowingError):
                self.growing().operate(
                    action, cycle=old, **({"seed": self.seed} if action == "plant" else {})
                )
            self.assertEqual(self.state(), before)
        with self.assertRaises(BerryGrowingError):
            self.growing().operate("harvest", cycle=self.growing().cycle(), seed=self.seed)
        self.assertEqual(self.state(), before)
        self.record("harvest")
        self.assertEqual(self.player.trainer.get_item_quantity(other), 1)

    def contention(self):
        """One purchased final seed and one harvest yield cannot be claimed twice."""
        self.buy(self.seed)
        outcomes = self.race(
            *(lambda: self.growing().operate("plant", cycle=None, seed=self.seed) for _ in range(2))
        )
        self.assertEqual(sum(outcome.get("changed", False) for outcome in outcomes), 1)
        self.assertEqual(self.player.trainer.get_item_quantity(self.seed), 0)
        cycle = self.growing().cycle()
        self.now += timedelta(hours=4)
        outcomes = self.race(
            *(lambda: self.growing().operate("harvest", cycle=cycle) for _ in range(2))
        )
        self.assertEqual(sum(outcome.get("changed", False) for outcome in outcomes), 1)
        self.assertEqual(self.player.trainer.get_item_quantity(self.seed), 1)

    def rollback(self):
        """Partial seed/harvest SQL and parent rollback preserve cycle, bag and notices."""
        from django.db import transaction

        self.buy(self.seed)
        before, messages = self.state(), len(self.player.messages)
        original = Trainer.remove_item

        def fail_after_debit(trainer, *args):
            """Perform the actual inventory write before returning failure."""
            original(trainer, *args)
            return False

        with patch.object(Trainer, "remove_item", fail_after_debit):
            self.record("plant " + self.seed)
        self.assertEqual(self.state(), before)
        with self.assertRaisesRegex(RuntimeError, "outer seed fixture"):
            with transaction.atomic():
                self.record("plant " + self.seed)
                self.assertFalse(
                    any(
                        "Planted one" in str(message) for message in self.player.messages[messages:]
                    )
                )
                raise RuntimeError("outer seed fixture")
        self.assertEqual(self.state(), before)
        self.record("plant " + self.seed)
        self.now += timedelta(hours=4)
        cycle, before = self.growing().cycle(), self.state()
        original_credit = Trainer.add_item

        def fail_after_credit(trainer, *args):
            """Fail after the actual canonical berry credit."""
            original_credit(trainer, *args)
            raise RuntimeError("post-credit seed fixture")

        with patch.object(Trainer, "add_item", fail_after_credit):
            with self.assertRaisesRegex(RuntimeError, "post-credit seed fixture"):
                self.growing().operate("harvest", cycle=cycle)
        self.assertEqual(self.state(), before)
        with self.assertRaisesRegex(RuntimeError, "outer harvest fixture"):
            with transaction.atomic():
                self.growing().operate("harvest", cycle=cycle)
                raise RuntimeError("outer harvest fixture")
        self.assertEqual(self.state(), before)
        self.record("harvest")
        self.assertEqual(self.player.trainer.get_item_quantity(self.seed), 1)

    def current_guards(self):
        """Owner/location/battle checks, held-only seeds and changed saved identity reject."""
        self.buy(self.seed)
        before = self.state()
        self.player.db.battle_lock = "new-seed-guard"
        self.record("plant " + self.seed)
        self.assertEqual(self.state(), before)
        self.player.db.battle_lock = None
        ObjectDB.objects.filter(pk=self.player.pk).update(db_location_id=None)
        self.record("plant " + self.seed)
        self.assertEqual(self.state(), before)
        ObjectDB.objects.filter(pk=self.player.pk).update(db_location_id=self.room.pk)
        self.record("plant " + self.seed)
        cycle, before = self.growing().cycle(), self.state()
        with self.assertRaises(BerryGrowingError):
            BerryGrowing(self.players[1], clock=lambda: self.now).operate("water", cycle=cycle)
        self.assertEqual(self.state(), before)
        for berry in ("Razz Berry", "cheriberry", "Bicycle"):
            BerryBed.objects.filter(trainer=self.player.trainer).update(berry=berry)
            invalid = self.state()
            self.record("harvest")
            self.assertEqual(self.state(), invalid)
        BerryBed.objects.filter(trainer=self.player.trainer).update(berry=self.seed)

    def counter(self):
        """Actual seeds exit/purchase/crop/cure alongside an unchanged old nursery."""
        from evennia.utils.create import create_object
        from pokemon.services.battle_rewards import BattleRewards
        from pokemon.services.item_counter import ItemCounter, BerryNursery
        from django.db import transaction

        hub = create_object(
            "typeclasses.rooms.FusionRoom", key="new-seed-hub-" + self.seed, nohome=True
        )
        counter = ItemCounter("world/berry_seed_counter.json")
        old = BerryNursery.install(hub)
        old_stock = BattleRewards.stored_attribute(old, "store_inventory")
        marker = "counter_status-berry-seed-counter-v1"
        count = ObjectDB.objects.count()
        with self.assertRaisesRegex(RuntimeError, "outer counter fixture"):
            with transaction.atomic():
                counter.install(hub)
                raise RuntimeError("outer counter fixture")
        self.assertEqual(ObjectDB.objects.count(), count)
        self.assertIsNone(BattleRewards.stored_attribute(hub, marker))
        self.assertIsNone(hub.attributes.get(marker))
        new = counter.install(hub)
        self.installed_objects.append(hub.pk)
        for marker in ("counter_oran-razz-nursery-v1", "counter_status-berry-seed-counter-v1"):
            receipt = BattleRewards.stored_attribute(hub, marker)
            self.installed_objects.extend(
                [receipt["room"], receipt["entrance"], receipt["return_exit"]]
            )
        self.room = new
        self.player.location = hub
        self.player.character.location = hub

        def move(destination, **kwargs):
            """Adapt only socket transport, persisting normal production movement."""
            moved = self.player.character.move_to(destination, quiet=True, move_hooks=False)
            if moved:
                self.player.location = destination
            return moved

        self.player.move_to = move
        entrance = ObjectDB.objects.get(db_location=hub, db_key="seeds")
        command = entrance.exit_command()
        command.caller, command.obj, command.args = self.player, entrance, ""
        command.func()
        self.assertEqual(
            ObjectDB.objects.filter(pk=self.player.pk)
            .values_list("db_location_id", flat=True)
            .get(),
            new.pk,
        )
        self.plant()
        before = self.state()
        self.assertEqual(counter.install(hub).pk, new.pk)
        self.assertEqual(self.state(), before)
        self.assertEqual(BattleRewards.stored_attribute(old, "store_inventory"), old_stock)
        for _ in range(4):
            self.record("water")
            self.now += timedelta(hours=1)
        self.record("harvest")
        self.assertEqual(self.player.trainer.get_item_quantity(self.seed), 5)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(status=SEEDS[self.seed])
        self.command("use", self.seed + "=3")
        self.assertEqual(self.player.trainer.get_item_quantity(self.seed), 4)
        self.assertEqual(
            OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("status", flat=True).get(), ""
        )
        self.assertEqual(BattleRewards.stored_attribute(old, "store_inventory"), old_stock)


def add_case(seed, label, method, *args):
    """Expose each accepted seed/mask/guard as its own independently counted case."""

    def test(self):
        """Run this seed's actual ordinary command lifecycle or safety control."""
        getattr(self, method)(*args)

    case_type = CASE_TYPES.setdefault(
        seed, type("Seed" + seed.split()[0], (SeedGrowingCases,), {"seed": seed})
    )
    setattr(case_type, "test_" + label, test)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        acquisition.load_runtime()
        import evennia
        from evennia.commands.command import Command

        with patch.object(evennia, "Command", Command):
            from commands.player import cmd_berry
        acquisition.COMMANDS["berry"] = (cmd_berry, cmd_berry.CmdBerry)
        from evennia.objects.models import ObjectDB
        from django.contrib.contenttypes.models import ContentType

        ContentType.objects.get_for_model(ObjectDB)
        from pokemon.models.berries import BerryBed
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.trainer import Trainer
        from pokemon.services.berry_growing import BerryGrowing, BerryGrowingError

        # Bind reused fixture helpers explicitly; do not run their __main__ setup.
        legacy.ObjectDB, legacy.BerryBed = ObjectDB, BerryBed
        legacy.OwnedPokemon, legacy.Trainer = OwnedPokemon, Trainer
        legacy.BerryGrowing, legacy.BerryGrowingError = BerryGrowing, BerryGrowingError
        CASE_TYPES = {}
        for seed in SEEDS:
            for mask in range(16):
                add_case(seed, "mask_" + str(mask), "masks", mask)
            for method in ("stale", "contention", "rollback", "current_guards", "counter"):
                add_case(seed, method, method)
        suite = unittest.TestSuite(
            unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in CASE_TYPES.values()
        )
        try:
            result = unittest.TextTestRunner(verbosity=2).run(suite)
        finally:
            if os.environ.get("PF2_NURSERY_SEED_EVIDENCE"):
                Path(os.environ["PF2_NURSERY_SEED_EVIDENCE"]).write_text(
                    json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8"
                )
        raise SystemExit(not result.wasSuccessful())

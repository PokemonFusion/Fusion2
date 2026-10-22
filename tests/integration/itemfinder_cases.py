"""Ordinary +hunt Potion delivery, replay and SQL failure/contention checks."""

import json
import os
from pathlib import Path
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import item_availability_cases as acquisition

EVIDENCE = []


class ItemfinderCases(unittest.TestCase):
    """Use production hunting/inventory/medicine with explicit disposable authoring."""

    tearDown = acquisition.AcquisitionCases.tearDown
    native = acquisition.AcquisitionCases.native
    state = acquisition.AcquisitionCases.state
    command = acquisition.AcquisitionCases.command

    def setUp(self):
        """Configure only Potion as an intentional test source with ordinary targets."""
        acquisition.AcquisitionCases.setUp(self)
        self.room.db.allow_hunting, self.room.db.noitem = True, False
        self.room.db.itemfinder_item, self.room.db.itemfinder_rate = "Potion", 100
        self.room.db.npc_chance, self.room.db.encounter_rate = 0, 0
        ObjectDB.objects.filter(pk=self.player.pk).update(db_location_id=self.room.pk)

    def claim(self, now=1000, roll=1):
        """Bind a fresh server attempt using a controllable test clock/roll only."""
        return ItemfinderClaim(self.player, self.room, clock=lambda: now,
                               rng=SimpleNamespace(randint=lambda *args: roll))

    def snapshot(self):
        """Read committed receipt and bag independently of retained Attribute values."""
        return {"state": self.state(), "receipt": BattleRewards.stored_attribute(self.player.character, ItemfinderClaim.key)}

    def test_hunt_inventory_use_and_reload(self):
        """A success message names an actual bag Potion that the ordinary command uses."""
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=1)
        before = self.snapshot()
        self.assertIn("found a Potion", self.command("hunt"))
        self.assertEqual(self.player.trainer.get_item_quantity("Potion"), 1)
        self.assertIn("Potion", self.command("inventory"))
        self.command("use", "Potion=3")
        self.assertEqual(self.player.trainer.get_item_quantity("Potion"), 0)
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("current_hp", flat=True).get(), 21)
        from django.db import connections
        connections.close_all()
        self.assertEqual(self.snapshot()["receipt"]["quantity"], 1)
        EVIDENCE.append({"label": "ordinary-finder-to-use", "commands": ["+hunt", "+inventory", "+use Potion=3", "SQL reload"],
                         "before": before, "after": self.snapshot(), "messages": list(map(str, self.player.messages))})

    def test_same_attempt_replay_and_old_attempt_after_newer_claim(self):
        """Retaining one latest receipt does not allow a replay to debit/credit again."""
        first = self.claim()
        first.claim()
        before = self.snapshot()
        self.assertIn("already completed", first.claim())
        self.assertEqual(self.snapshot(), before)
        self.claim(1003).claim()
        before = self.snapshot()
        self.assertIn("wait", first.claim())
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.player.trainer.get_item_quantity("Potion"), 2)

    def test_disabled_noitem_unknown_and_invalid_rate_grant_nothing(self):
        """Only a complete reviewed room rule may enable this source."""
        for key, value in (("allow_hunting", False), ("noitem", True),
                           ("itemfinder_item", "Mega Ring"), ("itemfinder_item", "Potion fragment"),
                           ("itemfinder_rate", True), ("itemfinder_rate", "100")):
            previous = getattr(self.room.db, key)
            setattr(self.room.db, key, value)
            before = self.snapshot()
            self.assertIsNone(self.claim().claim())
            self.assertEqual(self.snapshot(), before)
            setattr(self.room.db, key, previous)

    def test_failed_roll_is_a_durable_no_item_outcome(self):
        """A failed roll neither promises inventory nor becomes a second roll on retry."""
        self.room.db.itemfinder_rate = 5
        attempt = self.claim(roll=6)
        self.assertIsNone(attempt.claim())
        self.assertEqual(self.player.trainer.get_item_quantity("Potion"), 0)
        self.assertEqual(self.snapshot()["receipt"]["quantity"], 0)
        self.assertIn("already completed", attempt.claim())

    def test_post_credit_and_receipt_write_failures_roll_back(self):
        """Claim state and real inventory SQL share a transaction including partial writes."""
        from evennia.typeclasses.models import Attribute

        original_add, original_save = Trainer.add_item, Attribute.save

        def credit_then_fail(trainer, *args):
            """Fail after real bag credit."""
            original_add(trainer, *args)
            raise RuntimeError("finder credit fixture")

        def receipt_then_fail(attribute, *args, **kwargs):
            """Fail after the real receipt row save."""
            original_save(attribute, *args, **kwargs)
            if attribute.db_key == ItemfinderClaim.key:
                raise RuntimeError("finder receipt fixture")

        for target, name, failure in ((Trainer, "add_item", credit_then_fail), (Attribute, "save", receipt_then_fail)):
            before = self.snapshot()
            attempt = self.claim()
            with patch.object(target, name, failure), self.assertRaises(RuntimeError):
                attempt.claim()
            self.assertEqual(self.snapshot(), before)
            self.assertEqual(dict(self.player.db.inventory or {}), {})

    def test_competing_claims_inside_persistent_cooldown_credit_once(self):
        """Two independent worker connections cannot win the same search interval."""
        from django.db import close_old_connections

        barrier = Barrier(2)
        attempts = [self.claim(), self.claim()]

        def run(attempt):
            """Synchronize before owner-row claim locks, then close each connection."""
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return attempt.claim()
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(run, attempts))
        self.assertEqual(sum("found a Potion" in value for value in results), 1)
        self.assertEqual(self.player.trainer.get_item_quantity("Potion"), 1)
        EVIDENCE.append({"label": "finder-contention", "results": results, "after": self.snapshot()})

    def test_reconnect_cooldown_and_wrong_room_cannot_repeat_source(self):
        """Transient last_hunt_time is not the authority for successful claim spacing."""
        self.claim().claim()
        self.player.ndb.last_hunt_time = None
        before = self.snapshot()
        self.assertIn("wait", self.claim(1002).claim())
        self.assertEqual(self.snapshot(), before)
        ObjectDB.objects.filter(pk=self.player.pk).update(db_location_id=None)
        self.assertIn("no longer", self.claim(1003).claim())
        self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        acquisition.load_runtime()
        from evennia.objects.models import ObjectDB
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.trainer import Trainer
        from pokemon.services.battle_rewards import BattleRewards
        from pokemon.services.itemfinder import ItemfinderClaim

        try:
            result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ItemfinderCases))
        finally:
            if os.environ.get("PF2_ITEMFINDER_EVIDENCE"):
                Path(os.environ["PF2_ITEMFINDER_EVIDENCE"]).write_text(json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())

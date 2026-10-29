"""Named training Finder drops, real bag-to-use effects and explicit public routes."""

from dataclasses import replace
import json
import os
from pathlib import Path
import random
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
import item_availability_cases as acquisition
import itemfinder_cases as finder


class TrainingFinderCases(finder.ItemfinderCases):
    """Keep the original durable Finder controls while testing all fifteen names."""

    def setUp(self):
        """Prepare a private five-percent named source, no species or item expansion."""
        super().setUp()
        self.room.db.itemfinder_item = ""
        self.room.db.itemfinder_profile = "training-v1"
        self.room.db.itemfinder_rate = 5

    def claim(self, now=1000, roll=1, weighted=1):
        """Control only two labelled random draws; all actual grants use production SQL."""
        rolls = iter((roll, weighted))
        return finder.ItemfinderClaim(self.player, self.room, clock=lambda: now,
                                      rng=SimpleNamespace(randint=lambda *_: next(rolls)))

    def test_hunt_inventory_use_and_reload(self):
        """Every named drop reaches the real bag and an existing useful ordinary use."""
        from django.db import connection
        from pokemon.services.itemfinder import FinderProfile

        baseline = finder.OwnedPokemon.objects.values("level", "total_exp").get(pk=self.mon.pk)
        cumulative = 0
        for item, weight in FinderProfile.training:
            with self.subTest(item=item):
                cumulative += weight
                evs = [20] * 6 if item.endswith("Berry") else [0] * 6
                finder.OwnedPokemon.objects.filter(pk=self.mon.pk).update(
                    evs=evs, friendship=0, flags=[], current_hp=1, **baseline)
                self.player.character.attributes.remove(finder.ItemfinderClaim.key)
                self.player.ndb.last_hunt_time = None
                rolls = iter((5, cumulative))
                with patch.object(random, "randint", side_effect=lambda low, high:
                                      2 if (low, high) == (2, 5) else next(rolls)):
                    self.assertIn("found a " + item, self.command("hunt"))
                self.assertIn(item, self.command("inventory"))
                self.assertEqual(self.player.trainer.get_item_quantity(item), 1)
                before = self.state()
                target = "3/Attack" if item == "Bottle Cap" else "3"
                self.command("use", item + "=" + target)
                self.assertEqual(self.player.trainer.get_item_quantity(item), 0)
                self.assertNotEqual(self.state()["owned"], before["owned"])
                connection.close()
                self.assertEqual(self.snapshot()["receipt"]["item"], item)
                finder.EVIDENCE.append({"label": "training-finder-to-use", "item": item,
                    "rate": 5, "weighted_roll": cumulative, "before": before, "after": self.state(),
                    "transport": "captured ordinary commands, not logged-in sockets"})

    def test_same_attempt_replay_and_old_attempt_after_newer_claim(self):
        """Successful replay and expired attempts cannot award another feather."""
        first = self.claim()
        first.claim()
        before = self.snapshot()
        self.assertIn("already completed", first.claim())
        self.assertEqual(self.snapshot(), before)
        self.claim(1003).claim()
        before = self.snapshot()
        self.assertIn("wait", first.claim())
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.player.trainer.get_item_quantity("Health Feather"), 2)

    def test_competing_claims_inside_persistent_cooldown_credit_once(self):
        """Retain the real independent-connection race with named-reward assertions."""
        from concurrent.futures import ThreadPoolExecutor
        from django.db import connections
        from threading import Barrier

        attempts, barrier = [self.claim(), self.claim(weighted=100)], Barrier(2)

        def run(attempt):
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                return attempt.claim()
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(run, attempts))
        self.assertEqual(sum("You found" in str(value) for value in results), 1)
        total = sum(self.player.trainer.get_item_quantity(item) for item in ("Health Feather", "Gold Bottle Cap"))
        self.assertEqual(total, 1)

    def test_disabled_noitem_unknown_and_invalid_rate_grant_nothing(self):
        """Unknown/mixed configurations refuse without spending even the cooldown."""
        for key, value in (("allow_hunting", False), ("noitem", True),
                           ("itemfinder_item", "Potion"), ("itemfinder_profile", "unknown"),
                           ("itemfinder_rate", True), ("itemfinder_rate", 100)):
            old = getattr(self.room.db, key)
            setattr(self.room.db, key, value)
            before = self.snapshot()
            self.assertIsNone(self.claim().claim())
            self.assertEqual(self.snapshot(), before)
            setattr(self.room.db, key, old)

    def test_failed_roll_is_a_durable_no_item_outcome(self):
        """Six fails at exactly five percent and one stored attempt cannot reroll."""
        attempt = self.claim(roll=6)
        self.assertIsNone(attempt.claim())
        self.assertEqual(self.snapshot()["receipt"]["quantity"], 0)
        self.assertIn("already completed", attempt.claim())

    def test_public_activity_routes_are_atomic_idempotent_and_drift_refuses(self):
        """Explicit installation preserves context, ordinary traversal and existing source flags."""
        from django.db import transaction
        from evennia.utils.create import create_object
        from django.contrib.contenttypes.models import ContentType
        from pokemon.services.item_activity_routes import TRAINING_GROUNDS, TRAINING_TRAIL, DAY_GROVE, NIGHT_GROVE

        ContentType.objects.get_for_model(finder.ObjectDB)
        hub = create_object("typeclasses.rooms.FusionRoom", key="Private source hub", nohome=True)
        made = [hub.pk]
        self.addCleanup(lambda: finder.ObjectDB.objects.filter(pk__in=made).delete())
        for original in (TRAINING_GROUNDS, TRAINING_TRAIL, DAY_GROVE, NIGHT_GROVE):
            route = replace(original, key=original.key + "-" + uuid4().hex)
            with self.assertRaisesRegex(RuntimeError, "outer fixture"):
                with transaction.atomic():
                    route.install(hub)
                    raise RuntimeError("outer fixture rollback")
            self.assertFalse(finder.ObjectDB.objects.filter(db_tags__db_key=route.key).exists())
            room = route.install(hub)
            made.extend([room.pk, *finder.ObjectDB.objects.filter(db_destination=room).values_list("pk", flat=True),
                         *finder.ObjectDB.objects.filter(db_location=room).values_list("pk", flat=True)])
            self.assertEqual(route.install(hub).pk, room.pk)
            for key, value in route.attributes.items():
                self.assertEqual(finder.BattleRewards.stored_attribute(room, key), value)
            entrance = finder.ObjectDB.objects.get(db_location=hub, db_destination=room)
            returning = finder.ObjectDB.objects.get(db_location=room, db_destination=hub)
            for exit_row in (entrance, returning):
                self.assertTrue(exit_row.access(self.player.character, "traverse"))
                self.assertTrue(exit_row.access(self.player.character, "view"))
            self.player.character.move_to(hub, quiet=True)
            entrance.at_traverse(self.player.character, room)
            self.assertEqual(finder.ObjectDB.objects.values_list("db_location_id", flat=True).get(pk=self.player.pk), room.pk)
            returning.at_traverse(self.player.character, hub)
            self.assertEqual(finder.ObjectDB.objects.values_list("db_location_id", flat=True).get(pk=self.player.pk), hub.pk)
            key = next(iter(route.attributes))
            room.attributes.add(key, "changed")
            with self.assertRaisesRegex(ValueError, "configuration drift"):
                route.install(hub)
            self.assertEqual(finder.BattleRewards.stored_attribute(room, key), "changed")


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        acquisition.load_runtime()
        from evennia.objects.models import ObjectDB
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.trainer import Trainer
        from pokemon.services.battle_rewards import BattleRewards
        from pokemon.services.itemfinder import ItemfinderClaim

        for name in ("ObjectDB", "OwnedPokemon", "Trainer", "BattleRewards", "ItemfinderClaim"):
            setattr(finder, name, globals()[name])
        try:
            result = unittest.TextTestRunner(verbosity=2).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(TrainingFinderCases))
        finally:
            if os.environ.get("PF2_TRAINING_FINDER_EVIDENCE"):
                Path(os.environ["PF2_TRAINING_FINDER_EVIDENCE"]).write_text(
                    json.dumps(finder.EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())

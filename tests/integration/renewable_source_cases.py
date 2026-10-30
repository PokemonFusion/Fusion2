"""Exact five-percent opt-in sources, real elapsed cooldown, ordinary player routes."""

import json
import os
from pathlib import Path
import random
import time
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import item_availability_cases as acquisition
import itemfinder_cases as finder
import wild_held_item_cases as held


class NamedFinderCases(finder.ItemfinderCases):
    """Qualify exact named source configuration; retain all prior safety controls."""

    def setUp(self):
        """A labelled private named patch uses the reviewed five-percent rule."""
        super().setUp()
        self.room.db.itemfinder_rate = 5
        self.room.db.itemfinder_item = "Potion"
        self.room.db.allow_hunting, self.room.db.noitem = True, False
        finder.EVIDENCE.append(
            dict(
                label="separate-reviewed-named-source-setup",
                room=self.room.pk,
                room_name=self.room.key,
                allow_hunting=True,
                noitem=False,
                itemfinder_item="Potion",
                itemfinder_rate=5,
                npc_chance=0,
                encounter_rate=0,
                permanent=False,
            )
        )

    def test_hunt_inventory_use_and_reload(self):
        """The ordinary five-percent source hits under a controlled legal roll."""
        with patch.object(random, "randint", return_value=1):
            super().test_hunt_inventory_use_and_reload()

    def test_real_elapsed_cooldown_survives_connection_and_transient_cache_loss(self):
        """Actual wall time, not a forged receipt or accelerated timer, unlocks a later hunt."""
        from django.db import connection

        with patch.object(random, "randint", return_value=1):
            self.command("hunt")
            self.assertEqual(self.player.trainer.get_item_quantity("Potion"), 1)
            receipt = self.snapshot()["receipt"]
            self.player.ndb.last_hunt_time = None
            self.player.character.attributes.reset_cache()
            connection.close()
            self.command("hunt")
            self.assertEqual(self.player.trainer.get_item_quantity("Potion"), 1)
            self.assertEqual(self.snapshot()["receipt"], receipt)
            latest_attempt = max(receipt["started"], float(self.player.ndb.last_hunt_time or 0))
            remaining = max(0, latest_attempt + 3.1 - time.time())
            time.sleep(remaining)
            self.command("hunt")
        self.assertEqual(self.player.trainer.get_item_quantity("Potion"), 2)
        second = self.snapshot()["receipt"]
        self.assertGreaterEqual(second["started"] - receipt["started"], 3)
        finder.EVIDENCE.append(
            dict(
                label="real-elapsed-five-percent-finder",
                rate=5,
                elapsed=second["started"] - receipt["started"],
                quantity=2,
                commands=[
                    "+hunt",
                    "clear transient cooldown; close connection",
                    "+hunt rejected",
                    "wait real elapsed three seconds",
                    "+hunt",
                ],
                socket=False,
            )
        )

    def test_exact_five_percent_roll_boundary(self):
        """Roll five succeeds; six records a durable failed outcome with no reroll credit."""
        self.assertIn("found a Potion", self.claim(now=1000, roll=5).claim())
        self.assertEqual(self.player.trainer.get_item_quantity("Potion"), 1)
        miss = self.claim(now=1003, roll=6)
        self.assertIsNone(miss.claim())
        self.assertIn("already completed", miss.claim())
        self.assertEqual(self.player.trainer.get_item_quantity("Potion"), 1)

    def test_containing_rollback_cannot_announce_or_cache_a_phantom_potion(self):
        """Actual public hunt output must not promise a credit lost by an outer abort."""
        from django.db import transaction

        before, offset = self.snapshot(), len(self.player.messages)
        with patch.object(random, "randint", return_value=1):
            with self.assertRaisesRegex(RuntimeError, "outer finder"):
                with transaction.atomic():
                    self.command("hunt")
                    raise RuntimeError("outer finder")
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(
            any("found a Potion" in str(text) for text in self.player.messages[offset:])
        )


class NamedWildHeldCases(held.WildHeldItemCases):
    """Only the existing native level-five Rattata/Oran tuple is renewable."""

    def setUp(self):
        """Keep encounter/capture consumers real while selecting the legal success branch."""
        super().setUp()
        original = random.randint
        self.roll = patch.object(
            random,
            "randint",
            side_effect=lambda low, high: 1 if (low, high) == (1, 100) else original(low, high),
        )
        self.roll.start()
        self.addCleanup(self.roll.stop)

    def start(self, *, item="Oran Berry", chance=5, species="Rattata"):
        """Override only authored probability; all hunting and save/capture paths remain real."""
        pokemon = super().start(item=item, chance=chance, species=species)
        self.assertEqual(pokemon.level, 5)
        held.EVIDENCE.append(
            dict(
                label="separate-reviewed-native-held-source",
                room=self.room.pk,
                allow_hunting=True,
                noitem=bool(self.room.db.noitem),
                species=species,
                level=pokemon.level,
                item=item,
                held_item_chance=chance,
                chart=list(self.room.db.hunt_chart),
                permanent=False,
            )
        )
        return pokemon

    def test_exact_five_percent_held_roll_boundary(self):
        """The named tuple has the exact intended success/failure boundary."""
        from types import SimpleNamespace
        from pokemon.services.wild_held_items import WildHeldItems

        chart = {"held_item": "Oran Berry", "held_item_chance": 5}
        self.assertEqual(
            WildHeldItems.select("Rattata", chart, SimpleNamespace(randint=lambda *_: 5)),
            "Oran Berry",
        )
        self.assertEqual(
            WildHeldItems.select("Rattata", chart, SimpleNamespace(randint=lambda *_: 6)), ""
        )


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        acquisition.load_runtime()
        import evennia
        from evennia.commands.command import Command

        with patch.object(evennia, "Command", Command):
            from commands.player import cmd_battle_item, cmd_sheet
        acquisition.COMMANDS["item"] = (cmd_battle_item, cmd_battle_item.CmdBattleItem)
        acquisition.COMMANDS["party"] = (cmd_sheet, cmd_sheet.CmdSheetPokemon)
        from evennia.objects.models import ObjectDB
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle.capture import CaptureOutcome
        from pokemon.battle.handler import battle_handler
        from pokemon.models.core import OwnedPokemon, EncounterPokemon
        from pokemon.models.storage import CaptureReceipt
        from pokemon.models.trainer import Trainer
        from pokemon.names import normalize_name
        from pokemon.services.battle_rewards import BattleRewards
        from pokemon.services.capture import WildCaptureAttempt, finalize_wild_capture
        from pokemon.services.itemfinder import ItemfinderClaim

        for name in ("ObjectDB", "OwnedPokemon", "Trainer", "BattleRewards", "ItemfinderClaim"):
            setattr(finder, name, globals()[name])
        for name in (
            "BattleSession",
            "CaptureOutcome",
            "battle_handler",
            "OwnedPokemon",
            "EncounterPokemon",
            "CaptureReceipt",
            "normalize_name",
            "WildCaptureAttempt",
            "finalize_wild_capture",
        ):
            setattr(held, name, globals()[name])
        try:
            result = unittest.TextTestRunner(verbosity=2).run(
                unittest.TestSuite(
                    [
                        unittest.defaultTestLoader.loadTestsFromTestCase(NamedFinderCases),
                        unittest.defaultTestLoader.loadTestsFromTestCase(NamedWildHeldCases),
                    ]
                )
            )
        finally:
            if os.environ.get("PF2_RENEWABLE_SOURCE_EVIDENCE"):
                Path(os.environ["PF2_RENEWABLE_SOURCE_EVIDENCE"]).write_text(
                    json.dumps(
                        {"finder": finder.EVIDENCE, "held": held.EVIDENCE}, indent=2, default=str
                    )
                    + "\n",
                    encoding="utf-8",
                )
        raise SystemExit(not result.wasSuccessful())

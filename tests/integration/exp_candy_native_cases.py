"""Crossed base knowledge on both genuinely captured and combined Necrozma hosts."""

import importlib
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import necrozma_player_cases as native


class ExpCandyNativeCases(native.NecrozmaPlayerCases):
    """Keep all native regressions and add both deferred candy-learning lifecycles."""

    def candy(self, companion):
        """Capture, combine, earn base knowledge, separate and resume explicit choices."""
        from pokemon.services.exp_candy import CandyProgression
        from pokemon.services.item_learning import ItemLearning
        from pokemon.services.ownership import fresh_owned
        from pokemon.helpers.pokemon_helpers import get_max_hp
        from pokemon.models.stats import level_for_exp
        from pokemon.names import normalize_name

        self.acquire_pair(companion, level=30)
        ordinary = list(
            ActiveMoveslot.objects.filter(pokemon=self.host)
            .order_by("slot")
            .values("slot", "move_id", "current_pp")
        )
        self.combine()
        current = fresh_owned(self.host.pk)
        before = OwnedPokemon.objects.filter(pk=self.host.pk).values().get()
        earned = CandyProgression.crossed_moves(
            current, "Necrozma", 30, level_for_exp(before["total_exp"] + 30000)
        )
        self.assertTrue(earned)
        maximum = get_max_hp(current)
        OwnedPokemon.objects.filter(pk=self.host.pk).update(current_hp=maximum - 7)
        pp = list(ActiveMoveslot.objects.filter(pokemon=self.host).order_by("slot").values())
        resources = list(
            NecrozmaResource.objects.filter(host=self.host).order_by("source").values()
        )
        self.buy("Exp. Candy XL", price=30000, quantity=1)
        frozen = self.observation()
        self.record("use", "Exp. Candy XL=" + str(self.companion.pk))
        self.assertEqual(self.observation(), frozen)
        self.record("use", "Exp. Candy XL=3")
        after = OwnedPokemon.objects.filter(pk=self.host.pk).values().get()
        self.assertEqual(after["total_exp"], before["total_exp"] + 30000, self.player.messages[-5:])
        self.assertEqual(after["current_hp"], get_max_hp(fresh_owned(self.host.pk)) - 7)
        self.assertEqual(
            OwnedPokemon.objects.filter(pk=self.companion.pk).values().get(), self.partner_before
        )
        self.assertEqual(
            list(ActiveMoveslot.objects.filter(pokemon=self.host).order_by("slot").values()), pp
        )
        self.assertEqual(
            list(NecrozmaResource.objects.filter(host=self.host).order_by("source").values()),
            resources,
        )
        learned = {
            normalize_name(name) for name in self.host.learned_moves.values_list("name", flat=True)
        }
        self.assertTrue(all(normalize_name(name) in learned for _, name in earned))
        queue = ItemLearning(self.player)
        entries = queue.read()["entries"]
        self.assertEqual(
            [(row["level"], normalize_name(row["name"])) for row in entries],
            [(level, normalize_name(name)) for level, name in earned],
        )
        self.record("learn", "pending")
        self.assertTrue(all(row["token"] is None for row in queue.read()["entries"]))
        self.assertIn("until separation", "\n".join(map(str, self.player.messages[-3:])))
        self.separate()
        self.assertEqual(
            list(
                ActiveMoveslot.objects.filter(pokemon=self.host)
                .order_by("slot")
                .values("slot", "move_id", "current_pp")
            ),
            ordinary,
        )
        self.record("learn", "pending")
        entry = queue.read()["entries"][0]
        self.assertTrue(entry["token"])
        self.record("learn", "pending " + entry["token"] + "=store")
        self.assertEqual(
            OwnedPokemon.objects.filter(pk=self.host.pk).values_list("total_exp", flat=True).get(),
            after["total_exp"],
        )
        self.assertEqual(
            list(
                ActiveMoveslot.objects.filter(pokemon=self.host)
                .order_by("slot")
                .values("slot", "move_id", "current_pp")
            ),
            ordinary,
        )

    def test_dusk_candy_base_knowledge_is_deferred_until_separation(self):
        """Dusk Mane retains source and companion PP and stores only earned base knowledge."""
        self.candy("Solgaleo")

    def test_dawn_candy_base_knowledge_is_deferred_until_separation(self):
        """Dawn Wings retains source and companion PP and stores only earned base knowledge."""
        self.candy("Lunala")


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        native.core.load_runtime()
        from django.apps import apps
        from django.db import connection
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.models.necrozma import NecrozmaCombination, NecrozmaResource
        from pokemon.models.storage import PokemonPlacement
        from pokemon.services.placement_audit import audit_placements_v3

        # Existing isolated native-integrity fixture authority; no game migration.
        with connection.schema_editor() as editor:
            importlib.import_module("pokemon.migrations.0041_placement_integrity_triggers").install(
                apps, editor
            )
            importlib.import_module("pokemon.migrations.0058_necrozma_integrity").install(
                apps, editor
            )
        import evennia
        from evennia.commands.command import Command
        from evennia.commands.cmdset import CmdSet

        with patch.object(evennia, "Command", Command), patch.object(evennia, "CmdSet", CmdSet):
            from commands.player import (
                cmd_necrozma,
                cmd_battle_zmove,
                cmd_battle_concede,
                cmd_learn_evolve,
            )
        native.core.acquisition.COMMANDS.update(
            {
                "necrozma": (cmd_necrozma, cmd_necrozma.CmdNecrozma),
                "zmove": (cmd_battle_zmove, cmd_battle_zmove.CmdBattleZMove),
                "concede": (cmd_battle_concede, cmd_battle_concede.CmdBattleConcede),
                "learn": (cmd_learn_evolve, cmd_learn_evolve.CmdLearn),
            }
        )
        for name in (
            "apps",
            "OwnedPokemon",
            "ActiveMoveslot",
            "NecrozmaCombination",
            "NecrozmaResource",
            "PokemonPlacement",
            "audit_placements_v3",
        ):
            setattr(native, name, globals()[name])
        try:
            result = unittest.TextTestRunner(verbosity=2).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(ExpCandyNativeCases)
            )
        finally:
            if os.environ.get("PF2_EXP_CANDY_EVIDENCE"):
                Path(os.environ["PF2_EXP_CANDY_EVIDENCE"]).write_text(
                    json.dumps(native.core.EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8"
                )
        raise SystemExit(not result.wasSuccessful())

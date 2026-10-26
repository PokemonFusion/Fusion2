"""Paid mint training on both genuinely captured and combined native hosts."""

import importlib
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import necrozma_player_cases as native


class MintNativeCases(native.NecrozmaPlayerCases):
    """Keep native regressions while proving paid host training and frozen companion."""

    def train(self, species):
        """Capture, combine, buy, refuse companion, train host, rebuild and separate."""
        from pokemon.helpers.pokemon_helpers import get_max_hp, get_stats
        from pokemon.services.ownership import fresh_owned
        from utils.pokemon_utils import build_battle_pokemon_from_model

        self.acquire_pair(species)
        OwnedPokemon.objects.filter(pk=self.host.pk).update(nature="Jolly")
        OwnedPokemon.objects.filter(pk=self.companion.pk).update(
            nature="Bold", trained_stat_nature="Calm"
        )
        self.partner_before = OwnedPokemon.objects.filter(pk=self.companion.pk).values().get()
        self.combine()
        maximum = get_max_hp(fresh_owned(self.host.pk))
        OwnedPokemon.objects.filter(pk=self.host.pk).update(current_hp=maximum - 7)
        self.buy("Modest Mint", price=20000, quantity=1)
        before = self.observation()
        self.record("use", "Modest Mint=" + str(self.companion.pk))
        self.assertEqual(self.observation(), before)
        host_before = OwnedPokemon.objects.filter(pk=self.host.pk).values().get()
        pp = list(ActiveMoveslot.objects.filter(pokemon=self.host).order_by("slot").values())
        resources = list(
            NecrozmaResource.objects.filter(host=self.host).order_by("source").values()
        )
        self.record("use", "Modest Mint=3")
        after = OwnedPokemon.objects.filter(pk=self.host.pk).values().get()
        self.assertEqual(after["nature"], "Jolly")
        self.assertEqual(after["trained_stat_nature"], "Modest")
        self.assertEqual(after["current_hp"], get_max_hp(fresh_owned(self.host.pk)) - 7)
        for name, value in host_before.items():
            if name not in {"trained_stat_nature", "current_hp"}:
                self.assertEqual(after[name], value, name)
        self.assertEqual(self.player.trainer.get_item_quantity("Modest Mint"), 0)
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
        expected = get_stats(fresh_owned(self.host.pk))
        holder = build_battle_pokemon_from_model(fresh_owned(self.host.pk))
        self.assertEqual({key: getattr(holder.base_stats, key) for key in expected}, expected)
        from pokemon.battle.battledata import Pokemon

        restored = Pokemon.from_dict(holder.to_dict())
        self.assertEqual(restored.trained_stat_nature, "Modest")
        self.assertEqual(restored.nature, "Jolly")
        self.separate()
        self.assertEqual(fresh_owned(self.host.pk).trained_stat_nature, "Modest")
        self.assertEqual(fresh_owned(self.host.pk).nature, "Jolly")
        self.assertEqual(fresh_owned(self.companion.pk).trained_stat_nature, "Calm")
        native.core.EVIDENCE.append(
            dict(
                event="paid-mint-native-pair",
                companion=species,
                genetic="Jolly",
                trained="Modest",
                companion_training="Calm",
                battle_stats=expected,
                socket=False,
            )
        )

    def test_dusk_paid_mint_preserves_genetics_companion_and_source_pp(self):
        """The Dusk Mane lifecycle retains both independent Nature values."""
        self.train("Solgaleo")

    def test_dawn_paid_mint_preserves_genetics_companion_and_source_pp(self):
        """The Dawn Wings lifecycle retains both independent Nature values."""
        self.train("Lunala")


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

        # The pre-existing authorized random-schema 0041/0058 integrity fixtures;
        # this creates current model tables directly and applies no migration.
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
            from commands.player import cmd_necrozma, cmd_battle_zmove, cmd_battle_concede
        native.core.acquisition.COMMANDS.update(
            {
                "necrozma": (cmd_necrozma, cmd_necrozma.CmdNecrozma),
                "zmove": (cmd_battle_zmove, cmd_battle_zmove.CmdBattleZMove),
                "concede": (cmd_battle_concede, cmd_battle_concede.CmdBattleConcede),
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
                unittest.defaultTestLoader.loadTestsFromTestCase(MintNativeCases)
            )
        finally:
            if os.environ.get("PF2_NATURE_MINT_EVIDENCE"):
                Path(os.environ["PF2_NATURE_MINT_EVIDENCE"]).write_text(
                    json.dumps(native.core.EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8"
                )
        raise SystemExit(not result.wasSuccessful())

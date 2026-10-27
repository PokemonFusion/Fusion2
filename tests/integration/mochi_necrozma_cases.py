"""Mochi on both real captured/combined hosts with frozen-companion controls."""

import importlib
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import necrozma_player_cases as native

MOCHI = (
    ("Health Mochi", 0),
    ("Muscle Mochi", 1),
    ("Resist Mochi", 2),
    ("Genius Mochi", 3),
    ("Clever Mochi", 4),
    ("Swift Mochi", 5),
    ("Fresh-Start Mochi", None),
)


class MochiNativeCases(native.NecrozmaPlayerCases):
    """Retain all existing native regressions plus fourteen actual training flows."""

    def train(self, companion, item, index):
        """Capture, prepare labelled EVs, combine, refuse companion use, train/separate."""
        from pokemon.helpers.pokemon_helpers import get_max_hp
        from pokemon.services.ownership import fresh_owned

        self.acquire_pair(companion)
        evs = [10] * 6 if index is None else [0] * 6
        OwnedPokemon.objects.filter(pk=self.host.pk).update(evs=evs)
        maximum = get_max_hp(fresh_owned(self.host.pk))
        OwnedPokemon.objects.filter(pk=self.host.pk).update(current_hp=maximum - 7)
        ordinary = list(
            ActiveMoveslot.objects.filter(pokemon=self.host)
            .order_by("slot")
            .values("slot", "move_id", "current_pp")
        )
        native.core.EVIDENCE.append(
            {
                "event": "separate-mochi-prerequisite",
                "item": item,
                "host_evs": evs,
                "hp_deficit": 7,
                "native_capture": True,
            }
        )
        self.combine()
        self.buy(item, price=20000 if index is None else 10000, quantity=1)
        before = self.observation()
        self.record("use", item + "=" + str(self.companion.pk))
        self.assertEqual(self.observation(), before)
        self.assertEqual(self.player.trainer.get_item_quantity(item), 1)
        host_before = OwnedPokemon.objects.filter(pk=self.host.pk).values().get()
        pp = list(ActiveMoveslot.objects.filter(pokemon=self.host).order_by("slot").values())
        resources = list(
            NecrozmaResource.objects.filter(host=self.host).order_by("source").values()
        )
        self.record("use", item + "=3")
        after = OwnedPokemon.objects.filter(pk=self.host.pk).values().get()
        expected = [0] * 6
        if index is not None:
            expected[index] = 10
        self.assertEqual(after["evs"], expected)
        self.assertEqual(after["current_hp"], max(1, get_max_hp(fresh_owned(self.host.pk)) - 7))
        for key, value in host_before.items():
            if key not in {"evs", "current_hp"}:
                self.assertEqual(after[key], value, key)
        self.assertEqual(self.player.trainer.get_item_quantity(item), 0)
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
        OwnedPokemon.flush_cached_instance(self.host)
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.host.pk).values().get(), after)
        self.separate()
        self.assertEqual(
            OwnedPokemon.objects.filter(pk=self.host.pk).values_list("evs", flat=True).get(),
            expected,
        )
        self.assertEqual(
            list(
                ActiveMoveslot.objects.filter(pokemon=self.host)
                .order_by("slot")
                .values("slot", "move_id", "current_pp")
            ),
            ordinary,
        )


def add_case(companion, item, index):
    """Count each item and each genuinely captured native companion separately."""

    def test(self):
        """Use the named mochi on this paired host while preserving companion/PP custody."""
        self.train(companion, item, index)

    setattr(
        MochiNativeCases, "test_mochi_" + companion + "_" + item.split()[0].replace("-", ""), test
    )


for companion in ("Solgaleo", "Lunala"):
    for item, index in MOCHI:
        add_case(companion, item, index)


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

        # Same already-authorized disposable integrity fixtures as the native
        # suite; no migration is applied to a game or existing database.
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
                unittest.defaultTestLoader.loadTestsFromTestCase(MochiNativeCases)
            )
        finally:
            if os.environ.get("PF2_MOCHI_NATIVE_EVIDENCE"):
                Path(os.environ["PF2_MOCHI_NATIVE_EVIDENCE"]).write_text(
                    json.dumps(native.core.EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8"
                )
        raise SystemExit(not result.wasSuccessful())

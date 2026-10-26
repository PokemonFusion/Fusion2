"""Separate-connection competing Ultra confirmations on two genuine native hosts."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import importlib
import json
import os
from pathlib import Path
from threading import Barrier
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import ultra_battle_cases as ultra
import ultra_preparation_cases as preparation
import necrozma_player_cases as native


class UltraContentionCases(ultra.UltraBattleCases):
    """Exercise actual reviewed yes inputs, one side reservation and one activation."""

    def test_two_native_hosts_compete_for_one_side_without_duplicate_activation(self):
        """Two clients on the same controller cannot reserve Ultra for both active hosts."""
        from django.db import close_old_connections, connections, connection

        self.prepare("Solgaleo")
        self.session.end()
        self.session = None
        other_host = self.capture_source("Necrozma", 4)
        other_companion = self.capture_source("Lunala", 6)
        partner_before = OwnedPokemon.objects.filter(pk=other_companion.pk).values().get()
        self.mon = self.host
        self.record("teach", "4=Photon Geyser")
        if self.player.ndb._evmenu:
            self.reply("1")
        learned = list(other_host.learned_moves.values_list("name", flat=True))
        photon = next(name for name in learned if normalize_name(name) == "photongeyser")
        others = [name for name in learned if normalize_name(name) != "photongeyser"][:3]
        self.record("movesets")
        for answer in ("4", "1", ", ".join([photon, *others]), "back", "quit"):
            self.reply(answer)
        self.record("necrozma", "combine 4=6/2")
        self.reply("yes")
        self.buy("Ultranecrozium Z", price=100, quantity=1)
        self.record("hold", "4=Ultranecrozium Z")
        self.launch("double")
        self.refresh_actor()
        self.assertIn("Confirm", self.preview("A1"))
        first = self.preview_generator
        self.assertIn("Confirm", self.preview("A2"))
        second = self.preview_generator
        before_pp = list(
            ActiveMoveslot.objects.filter(pokemon_id__in=(self.host.pk, other_host.pk), slot=1)
            .order_by("pokemon_id")
            .values("pokemon_id", "current_pp")
        )
        barrier = Barrier(2)
        start = len(self.player.messages)

        def confirm(generator):
            """Resume the real player's reviewed command on an independent SQL connection."""
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    pid = cursor.fetchone()[0]
                barrier.wait(timeout=15)
                try:
                    generator.send("yes")
                except StopIteration:
                    pass
                return pid
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            pids = list(executor.map(confirm, (first, second)))
        self.assertEqual(len(set(pids)), 2)
        messages = list(map(str, self.player.messages[start:]))
        self.assertEqual(
            sum("Ultra Burst reserved" in message for message in messages), 1, messages
        )
        self.assertTrue(
            any("already has an Ultra declaration" in message for message in messages), messages
        )
        self.assertEqual(set(self.session.battle.ultra_pending), {"A"})
        winner = deepcopy(self.session.battle.ultra_pending["A"])
        self.assertFalse(self.session.battle.ultra_used)
        self.assertFalse(self.session.state.declare)
        self.assertEqual(
            before_pp,
            list(
                ActiveMoveslot.objects.filter(pokemon_id__in=(self.host.pk, other_host.pk), slot=1)
                .order_by("pokemon_id")
                .values("pokemon_id", "current_pp")
            ),
        )
        self.rebuild()
        self.assertEqual(self.session.battle.ultra_pending["A"], winner)
        with patch.object(self.session, "maybe_run_turn"):
            self.record("attack", "A1 Sunsteel Strike B1")
            self.record("attack", "A2 Moongeist Beam B1")
            self.record("attack", "B1 Growl A1", side=1)
            self.record("attack", "B2 Growl A1", side=1)
        self.session.execute_persistent_turn()
        native_hosts = [
            mon
            for mon in self.session.battle.participants[0].pokemons
            if mon.model_id in {"owned:" + str(self.host.pk), "owned:" + str(other_host.pk)}
        ]
        self.assertEqual(sum(str(mon.species) == "Necrozma-Ultra" for mon in native_hosts), 1)
        self.assertEqual(self.session.battle.ultra_used, {"A"})
        self.assertFalse(self.session.battle.z_used)
        self.assertEqual(
            before_pp,
            list(
                ActiveMoveslot.objects.filter(pokemon_id__in=(self.host.pk, other_host.pk), slot=1)
                .order_by("pokemon_id")
                .values("pokemon_id", "current_pp")
            ),
        )
        self.assertEqual(
            OwnedPokemon.objects.filter(pk=other_companion.pk).values().get(), partner_before
        )
        self.assertEqual(
            OwnedPokemon.objects.filter(pk=self.companion.pk).values().get(), self.partner_before
        )
        native.core.EVIDENCE.append(
            dict(
                case=self._testMethodName,
                event="two-native-host-separate-connection-confirmation",
                connection_count=2,
                winner=winner,
                messages=messages,
                activated_count=1,
                same_side_control="two ordinary command clients for the same owning player",
                photon_pp_unchanged=True,
            )
        )
        self.session.end()
        self.session = None
        self.record("necrozma", "separate 4")
        self.reply("yes")
        self.separate()
        self.assertEqual(
            OwnedPokemon.objects.filter(pk=other_companion.pk).values().get(), partner_before
        )


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
        from pokemon.names import normalize_name
        from pokemon.services.placement_audit import audit_placements_v3

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
                cmd_movesets,
                cmd_learn_evolve,
                cmd_battle_ultra,
            )
        native.core.acquisition.COMMANDS.update(
            {
                "necrozma": (cmd_necrozma, cmd_necrozma.CmdNecrozma),
                "zmove": (cmd_battle_zmove, cmd_battle_zmove.CmdBattleZMove),
                "concede": (cmd_battle_concede, cmd_battle_concede.CmdBattleConcede),
                "movesets": (cmd_movesets, cmd_movesets.CmdMovesets),
                "teach": (cmd_learn_evolve, cmd_learn_evolve.CmdTeachMove),
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
            "normalize_name",
        ):
            for module in (native, preparation, ultra):
                setattr(module, name, globals()[name])
        try:
            result = unittest.TextTestRunner(verbosity=2).run(
                unittest.TestSuite(
                    [
                        UltraContentionCases(
                            "test_two_native_hosts_compete_for_one_side_without_duplicate_activation"
                        )
                    ]
                )
            )
        finally:
            if os.environ.get("PF2_ULTRA_EVIDENCE"):
                Path(os.environ["PF2_ULTRA_EVIDENCE"]).write_text(
                    json.dumps(native.core.EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8"
                )
        raise SystemExit(not result.wasSuccessful())

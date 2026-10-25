"""Ordinary recovery/protection prerequisites through owned commands and real SQL."""

import json
import os
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import mega_evolution_cases as core
from mega_stone_cases import MegaStoneCases
from z_native_cases import NativeZCases
from z_special_sources_cases import SpecialZSourceCases


class HalfRoll(random.Random):
    """Labelled probability boundary for a legitimate repeated-Protect failure."""

    def random(self):
        return 0.5


class RecoveryMoveSourcesCases(unittest.TestCase):
    """Keep prerequisite HP/weather/fixtures separate from actual player turns."""

    command = core.MegaEvolutionCases.command
    reply = core.MegaEvolutionCases.reply
    state = core.MegaEvolutionCases.state
    native = core.MegaEvolutionCases.native
    buy = core.MegaEvolutionCases.buy
    record = core.MegaEvolutionCases.record
    observation = core.MegaEvolutionCases.observation
    launch = core.MegaEvolutionCases.launch
    rebuild = core.MegaEvolutionCases.rebuild
    fixture_native = MegaStoneCases.fixture_native
    acquire = SpecialZSourceCases.acquire
    setUp = NativeZCases.setUp
    tearDown = NativeZCases.tearDown

    def queue(self, source, reply):
        """Declare both ordinary actions without replacing their execution."""
        with patch.object(self.session, "maybe_run_turn"):
            self.record("attack", "A1 " + source + " A1")
            self.record(
                "attack",
                "B1 "
                + reply
                + (" A1" if reply in {"Mud-Slap", "Water Gun", "Tail Whip"} else " B1"),
                side=1,
            )

    def flow(self, source, facet):
        """Verify actual base effects, PP, current typing and checkpoint rollback."""
        from pokemon.models.moves import ActiveMoveslot

        native = {"Roost": "Pidgeot", "Synthesis": "Bulbasaur", "Protect": "Pelipper"}[source]
        self.mon = (
            self.acquire(native, source)
            if facet == "native"
            else self.fixture_native(native, [source], 3)
        )
        maximum = self.mon.get_max_hp()
        initial = maximum if facet == "full" else max(1, maximum // 4)
        core.OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=initial)
        core.OwnedPokemon.flush_cached_instance(self.mon)
        self.foe = self.fixture_native(
            "Wooper", ["Mud-Slap", "Water Gun", "Tail Whip"], 1, side=1, level=5
        )
        # Labelled native opponent ability prerequisite. Damp's unrelated
        # weather Damage callback assumes effect.id; retain its original failure.
        core.OwnedPokemon.objects.filter(pk=self.foe.pk).update(ability="Water Absorb")
        core.OwnedPokemon.flush_cached_instance(self.foe)
        if facet == "umbrella":
            self.buy("Utility Umbrella", price=10000, quantity=1)
            self.record("hold", "3=Utility Umbrella")
        self.launch("single")
        battle = self.session.battle
        holder = battle.participants[0].active[0]
        if facet in {"sunnyday", "raindance", "sandstorm", "snow", "umbrella"}:
            self.assertTrue(
                battle.setWeather(
                    "sunnyday" if facet == "umbrella" else facet,
                    source=battle.participants[1].active[0],
                )
            )
        if facet == "blocked":
            battle.apply_volatile_status(
                holder, "healblock", source=battle.participants[1].active[0]
            )
        core.EVIDENCE.append(
            {
                "case": self._testMethodName,
                "event": "separate-recovery-prerequisites",
                "source": source,
                "facet": facet,
                "initial_hp": initial,
                "maximum": maximum,
                "native_acquisition": facet == "native",
                "opponent_native_ability": "Water Absorb",
                "after": self.observation(),
            }
        )
        pp = ActiveMoveslot.objects.get(pokemon=self.mon, slot=1).current_pp
        response = (
            "Water Gun" if source == "Protect" else "Mud-Slap" if source == "Roost" else "Tail Whip"
        )
        self.queue(source, response)
        self.rebuild()
        before = self.observation()
        if facet == "checkpoint_fault":
            original = self.session.storage.set

            def fail_save(name, value):
                """Fail only after real owned effect synchronization."""
                if name == "data":
                    raise RuntimeError("ordinary recovery checkpoint fault")
                return original(name, value)

            with (
                patch.object(self.session.storage, "set", side_effect=fail_save),
                self.assertRaisesRegex(RuntimeError, "recovery checkpoint"),
            ):
                self.session.execute_persistent_turn()
            self.assertEqual(self.observation(), before)
        self.session.battle.rng = random.Random(12)
        self.session.execute_persistent_turn()
        self.mon.refresh_from_db()
        user = self.session.battle.participants[0].active[0]
        spent = facet != "blocked"
        self.assertEqual(
            ActiveMoveslot.objects.get(pokemon=self.mon, slot=1).current_pp, pp - int(spent)
        )
        if source == "Synthesis":
            numerator, denominator = (
                (2, 3)
                if facet == "sunnyday"
                else (1, 4) if facet in {"raindance", "sandstorm", "snow"} else (1, 2)
            )
            expected = (
                initial
                if facet in {"full", "blocked"}
                else min(maximum, initial + maximum * numerator // denominator)
            )
            if facet == "sandstorm":
                expected -= max(1, maximum // 16)  # Ordinary residual damage after the useful heal.
            self.assertEqual(self.mon.current_hp, expected)
        elif source == "Roost":
            if facet in {"full", "blocked"}:
                self.assertEqual(self.mon.current_hp, initial)
            else:
                self.assertGreater(self.mon.current_hp, initial)
                self.assertLess(self.mon.current_hp, min(maximum, initial + maximum // 2))
            self.assertIn("Flying", user.types)
            self.assertNotIn("roost", user.volatiles)
        else:
            self.assertEqual(self.mon.current_hp, initial)
            if facet == "repeat":
                self.rebuild()
                self.assertEqual(
                    self.session.battle.participants[0].active[0].volatiles["stall"]["counter"], 3
                )
                self.queue(source, "Water Gun")
                self.session.battle.rng = HalfRoll(1)
                self.session.execute_persistent_turn()
                self.mon.refresh_from_db()
                self.assertLess(self.mon.current_hp, initial)
                self.assertEqual(
                    ActiveMoveslot.objects.get(pokemon=self.mon, slot=1).current_pp, pp - 2
                )
        self.assertFalse(getattr(self.session.battle, "_callback_failures", []))
        core.EVIDENCE.append(
            {
                "case": self._testMethodName,
                "event": "ordinary-recovery-effect",
                "source": source,
                "facet": facet,
                "hp_before": initial,
                "hp_after": self.mon.current_hp,
                "pp_before": pp,
                "pp_after": ActiveMoveslot.objects.get(pokemon=self.mon, slot=1).current_pp,
                "types": list(user.types),
                "after": self.observation(),
            }
        )
        self.rebuild()
        self.session.end()
        self.session = None
        if facet == "umbrella":
            self.record("hold", "3=")
            self.assertEqual(self.player.trainer.get_item_quantity("Utility Umbrella"), 1)


for source, facets in [
    ("Roost", ["native", "active", "full", "blocked", "checkpoint_fault"]),
    (
        "Synthesis",
        [
            "native",
            "active",
            "full",
            "blocked",
            "sunnyday",
            "raindance",
            "sandstorm",
            "snow",
            "umbrella",
            "checkpoint_fault",
        ],
    ),
    ("Protect", ["native", "active", "repeat", "checkpoint_fault"]),
]:
    for facet in facets:

        def test(self, source=source, facet=facet):
            """One isolated native source and actual complete-turn outcome."""
            self.flow(source, facet)

        setattr(RecoveryMoveSourcesCases, "test_" + source.lower() + "_" + facet, test)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        core.load_runtime()
        import evennia
        from evennia.commands.command import Command
        from evennia.commands.cmdset import CmdSet

        with patch.object(evennia, "Command", Command), patch.object(evennia, "CmdSet", CmdSet):
            from commands.player import cmd_battle_item, cmd_learn_evolve, cmd_movesets
        core.acquisition.COMMANDS.update(
            {
                "item": (cmd_battle_item, cmd_battle_item.CmdBattleItem),
                "teach": (cmd_learn_evolve, cmd_learn_evolve.CmdTeachMove),
                "movesets": (cmd_movesets, cmd_movesets.CmdMovesets),
            }
        )
        try:
            result = unittest.TextTestRunner(verbosity=2, failfast=True).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(RecoveryMoveSourcesCases)
            )
        finally:
            if os.environ.get("PF2_Z_EVIDENCE"):
                Path(os.environ["PF2_Z_EVIDENCE"]).write_text(
                    json.dumps(core.EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8"
                )
        raise SystemExit(not result.wasSuccessful())

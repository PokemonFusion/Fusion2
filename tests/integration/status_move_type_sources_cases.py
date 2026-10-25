"""Ordinary Thunder Wave target/status/PP controls before its new Z source."""

import json
import os
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import mega_evolution_cases as core
from z_native_cases import NativeZCases
from mega_stone_cases import MegaStoneCases


class StatusMoveTypeSourcesCases(unittest.TestCase):
    """Retain actual owned source identity through commands, SQL and reconnection."""

    command = core.MegaEvolutionCases.command
    reply = core.MegaEvolutionCases.reply
    state = core.MegaEvolutionCases.state
    native = core.MegaEvolutionCases.native
    observation = core.MegaEvolutionCases.observation
    record = core.MegaEvolutionCases.record
    launch = core.MegaEvolutionCases.launch
    rebuild = core.MegaEvolutionCases.rebuild
    fixture_native = MegaStoneCases.fixture_native
    setUp = NativeZCases.setUp
    tearDown = NativeZCases.tearDown

    def flow(self, species, passive, paralyzed):
        """Execute a native active Thunder Wave and inspect durable status/PP once."""
        from pokemon.models.moves import ActiveMoveslot

        self.mon = self.fixture_native("Mareep", ["Thunder Wave"], 3, level=100)
        self.foe = self.fixture_native(species, [passive], 1, side=1, level=100)
        self.launch("single")
        pp = ActiveMoveslot.objects.get(pokemon=self.mon, slot=1).current_pp
        with patch.object(self.session, "maybe_run_turn"):
            self.record("attack", "A1 Thunder Wave B1")
            self.record(
                "attack", "B1 " + passive + (" B1" if passive == "Splash" else " A1"), side=1
            )
        self.rebuild()
        self.session.battle.rng = random.Random(12)
        self.session.execute_persistent_turn()
        self.foe.refresh_from_db()
        self.assertEqual(self.foe.status == "par", paralyzed)
        self.assertEqual(ActiveMoveslot.objects.get(pokemon=self.mon, slot=1).current_pp, pp - 1)
        self.assertFalse(self.session.battle.z_used)
        self.assertFalse(getattr(self.session.battle, "_callback_failures", []))
        core.EVIDENCE.append(
            {
                "case": self._testMethodName,
                "event": "ordinary-status-type-effect",
                "source": "Thunder Wave",
                "target": species,
                "target_status": self.foe.status,
                "source_pp_before": pp,
                "source_pp_after": pp - 1,
                "after": self.observation(),
            }
        )
        self.rebuild()
        self.foe.refresh_from_db()
        self.assertEqual(self.foe.status == "par", paralyzed)
        self.session.end()
        self.session = None


for species, passive, paralyzed in [
    ("Diglett", "Sand Attack", False),
    ("Jolteon", "Tail Whip", False),
    ("Wailord", "Splash", True),
]:

    def test(self, species=species, passive=passive, paralyzed=paralyzed):
        """One native positive or relevant Ground/Electric immunity control."""
        self.flow(species, passive, paralyzed)

    setattr(StatusMoveTypeSourcesCases, "test_thunderwave_" + species.lower(), test)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        core.load_runtime()
        try:
            result = unittest.TextTestRunner(verbosity=2, failfast=True).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(StatusMoveTypeSourcesCases)
            )
        finally:
            if os.environ.get("PF2_Z_EVIDENCE"):
                Path(os.environ["PF2_Z_EVIDENCE"]).write_text(
                    json.dumps(core.EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8"
                )
        raise SystemExit(not result.wasSuccessful())

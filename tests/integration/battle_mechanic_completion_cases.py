"""Existing reusable Mega/Z items through the last KO and ordinary battle end."""

import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import mega_evolution_cases as core


class MechanicCompletionCases(unittest.TestCase):
    """The completed-battle ownership check may validate cleanup, never activate."""

    setUp = core.MegaEvolutionCases.setUp
    tearDown = core.MegaEvolutionCases.tearDown
    native = core.MegaEvolutionCases.native
    command = core.MegaEvolutionCases.command
    state = core.MegaEvolutionCases.state
    buy = core.MegaEvolutionCases.buy
    reply = core.MegaEvolutionCases.reply
    record = core.MegaEvolutionCases.record
    observation = core.MegaEvolutionCases.observation
    launch = core.MegaEvolutionCases.launch

    def complete(self, crystal, mechanic):
        """Buy/equip, reserve/attack, final real KO, completed guard and end."""
        for placement in list(
            self.players[1]
            .storage.placements.filter(location_type="party")
            .exclude(pokemon=self.foe)
        ):
            core.PlacementService(self.players[1].storage).to_box(placement.pokemon)
        core.OwnedPokemon.objects.filter(pk=self.foe.pk).update(current_hp=1)
        self.foe.refresh_from_db()
        core.EVIDENCE.append(
            dict(
                case=self._testMethodName,
                fixture="one ordinary opponent with labelled HP1 before battle",
            )
        )
        self.buy(crystal, price=100, quantity=1)
        self.record("hold", "3=" + crystal)
        self.launch()
        with patch.object(self.session, "maybe_run_turn"):
            if mechanic == "mega":
                self.record("mega")
                self.record("attack", "Tackle B1")
            else:
                self.record("zmove", "Tackle=B1")
            self.record("attack", "Growl A1", side=1)
        self.session.execute_persistent_turn()
        self.assertTrue(self.session.battle.battle_over)
        self.assertEqual(getattr(self.session.battle, mechanic + "_used"), {"A"})
        from pokemon.battle.owned_battle_actor import OwnedBattleActor

        participant = self.session.battle.participants[0]
        actor = participant.active[0]
        with self.assertRaisesRegex(ValueError, "does not support"):
            with OwnedBattleActor.locked(self.session.battle, participant, actor):
                self.fail("A completed battle must not authorize another activation.")
        battle = self.session.battle
        self.session.end()
        self.session = None
        self.assertEqual(actor.species, "Venusaur")
        self.assertEqual(getattr(battle, mechanic + "_used"), {"A"})
        self.record("hold", "3=")
        self.assertEqual(self.player.trainer.get_item_quantity(crystal), 1)

    def test_existing_mega_final_ko_and_completed_cleanup(self):
        self.complete("Venusaurite", "mega")

    def test_existing_z_final_ko_and_completed_cleanup(self):
        self.complete("Normalium Z", "z")


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        core.load_runtime()
        import evennia
        from evennia.commands.command import Command

        with patch.object(evennia, "Command", Command):
            from commands.player import cmd_battle_zmove
        core.acquisition.COMMANDS["zmove"] = (cmd_battle_zmove, cmd_battle_zmove.CmdBattleZMove)
        try:
            result = unittest.TextTestRunner(verbosity=2).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(MechanicCompletionCases)
            )
        finally:
            if os.environ.get("PF2_ULTRA_EVIDENCE"):
                Path(os.environ["PF2_ULTRA_EVIDENCE"]).write_text(
                    json.dumps(core.EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8"
                )
        raise SystemExit(not result.wasSuccessful())

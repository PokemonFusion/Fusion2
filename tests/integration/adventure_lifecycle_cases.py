"""Real Adventure battle startup/concession recovery in disposable PostgreSQL."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
from ui_cases import PlayerView


class AdventureLifecycleCases(unittest.TestCase):
    """Keep recovery identity and cleanup safe at command/session boundaries."""

    def setUp(self):
        """Create an ordinary player, room and owned party in the test schema."""
        character = ObjectDB.objects.create(db_key="Adventure QA " + uuid4().hex[:8])
        self.trainer = Trainer.objects.create(user=character, trainer_number=Trainer.objects.count() + 1)
        storage = UserStorage.objects.create(user=character)
        self.player = PlayerView(character, self.trainer, storage)
        self.player.location = ObjectDB.objects.create(db_key="Adventure room " + uuid4().hex[:8])
        create_owned_pokemon("Squirtle", self.trainer, 5, ivs=[0] * 6, evs=[0] * 6, active_move_names=["Watergun"])
        self.adventure = AdventureSession.objects.create(leader=character, template_key="alpha_meadow", current_node="fork")
        self.choice = SimpleNamespace(species="Rattata", level=5, encounter_kind="wild", opponent_name="", key="wild", outcome_key="wild_route")

    def tearDown(self):
        """Release retained test battles without applying an Adventure result."""
        instance = getattr(self.player.ndb, "battle_instance", None)
        if instance:
            instance.encounter_metadata = {}
            instance._adventure_result = None
            instance.end()

    def choose(self):
        """Run the production route command with a valid committed route choice."""
        command = CmdAdventure()
        command.caller = self.player
        result = AdventureActionResult(True, "Route chosen.", self.adventure, self.choice)
        with patch("pokemon.adventures.commands.choose_session_route", return_value=result):
            command._choose("wild")

    def start(self):
        """Start the actual encounter using real session persistence."""
        instance = BattleSession(self.player)
        instance.start_adventure_encounter(
            species="Rattata", level=5, encounter_kind="wild", opponent_name="",
            adventure_session_id=self.adventure.pk, route_key="wild", outcome_key="wild_route",
        )
        return instance

    def concede(self, instance):
        """Use the real concession command and canonical manager."""
        command = CmdBattleConcede()
        command.caller = self.player
        command._finalize_concession(instance, battle_handler)

    def test_generation_failure_releases_lock_and_same_route_can_retry(self):
        """A constructor-registered session must not block the advertised retry."""
        with patch("pokemon.battle.battleinstance.create_battle_pokemon", side_effect=RuntimeError("generation failed")):
            self.choose()
        self.assertIsNone(self.player.ndb.battle_instance)
        self.assertIsNone(self.player.db.battle_lock)
        self.assertFalse(self.player.location.db.battles)
        self.choose()
        self.assertIsNotNone(self.player.ndb.battle_instance)
        self.assertTrue(self.player.db.battle_control)

    def test_failure_after_registration_cleans_up_encounter_and_room_state(self):
        """A late startup error must release both the manager and temporary row."""
        original = BattleSession._setup_battle_room
        instances = []

        def expose_then_fail(instance, *args, **kwargs):
            instances.append(instance)
            original(instance, *args, **kwargs)
            raise RuntimeError("late startup failure")

        before = EncounterPokemon.objects.count()
        with patch.object(BattleSession, "_setup_battle_room", expose_then_fail):
            self.choose()
        instance = instances[0]
        self.assertIsNone(battle_handler.get(instance.battle_id))
        self.assertIsNone(self.player.ndb.battle_instance)
        self.assertIsNone(instance.storage.get("data"))
        self.assertEqual(EncounterPokemon.objects.count(), before)

    def test_startup_cleanup_outage_can_be_retried_by_player_command(self):
        """A failed initial cleanup still exposes the ordinary recovery command."""
        with patch("pokemon.battle.battleinstance.create_battle_pokemon", side_effect=RuntimeError("generation failed")), patch.object(BattleSession, "end", side_effect=RuntimeError("cleanup unavailable")):
            self.choose()
        self.assertTrue(self.player.ndb.battle_instance._startup_failed)
        command = CmdAdventure()
        command.caller = self.player
        command._retry()
        self.assertIsNone(self.player.ndb.battle_instance)
        self.assertIsNone(self.player.db.battle_lock)

    def test_adventure_identity_is_saved_before_launch_and_first_prompt(self):
        """The first playable/persisted state already identifies its Adventure."""
        original = BattleSession._setup_battle_room
        snapshots = []

        def check_identity(instance, *args, **kwargs):
            saved = dict(instance.storage.get("encounter") or {})
            self.assertEqual(saved.get("source_type"), "adventure")
            self.assertEqual(saved.get("adventure_session_id"), self.adventure.pk)
            self.assertEqual(saved, instance.encounter_metadata)
            snapshots.append(saved)
            return original(instance, *args, **kwargs)

        with patch.object(BattleSession, "_setup_battle_room", check_identity):
            self.start()
        self.assertEqual(len(snapshots), 1)

    def test_metadata_write_failure_never_exposes_a_turn(self):
        """If identity cannot be saved, the player cannot enter an anonymous battle."""
        instance = BattleSession(self.player)
        original_set = instance.storage.set

        def fail_identity(part, value):
            if part == "encounter":
                raise RuntimeError("identity unavailable")
            return original_set(part, value)

        with patch.object(instance.storage, "set", side_effect=fail_identity), patch.object(instance, "_setup_battle_room") as expose:
            with self.assertRaises(RuntimeError):
                instance.start_adventure_encounter(
                    species="Rattata", level=5, encounter_kind="wild", opponent_name="",
                    adventure_session_id=self.adventure.pk, route_key="wild", outcome_key="wild_route",
                )
        expose.assert_not_called()

    def test_concession_preserves_original_session_when_receipt_write_fails(self):
        """A failed durable loss must leave the sole result copy and input usable."""
        instance = self.start()
        original_data = instance.storage.get("data")
        with patch("pokemon.adventures.sessions.queue_encounter_result", side_effect=RuntimeError("receipt unavailable")):
            self.concede(instance)
        self.assertIs(battle_handler.get(instance.battle_id), instance)
        self.assertIs(self.player.ndb.battle_instance, instance)
        self.assertEqual(instance.storage.get("data"), original_data)
        self.assertEqual(instance._adventure_result, "loss")
        self.assertFalse(self.player.db.battle_control)

    def test_concession_records_before_one_cleanup_and_leaves_retry_receipt(self):
        """Unresolved outcomes survive normal manager cleanup without double end."""
        instance = self.start()
        original_end = instance.end
        calls = []

        def check_then_end():
            calls.append("cleanup")
            pending = dict(self.player.db.pending_adventure_results or {})
            self.assertEqual(pending.get(str(self.adventure.pk)), "loss")
            return original_end()

        with patch("pokemon.adventures.sessions.resolve_encounter_result", return_value=AdventureActionResult(False, "retry needed")), patch.object(instance, "end", check_then_end):
            self.concede(instance)
        self.assertEqual(calls, ["cleanup"])
        self.assertIsNone(battle_handler.get(instance.battle_id))
        self.assertEqual(dict(self.player.db.pending_adventure_results), {str(self.adventure.pk): "loss"})

    def test_committed_capture_replay_records_capture_after_memory_loss(self):
        """A replay with its last ball spent must still resolve as capture, not win."""
        instance = self.start()
        actor, foe = instance.battle.participants
        target = foe.active[0]
        self.trainer.add_item("masterball", 1)
        WildCaptureAttempt(target_poke=target, player=self.player, trainer=self.trainer, battle_context=instance, ball_name="Master Ball").resolve(
            roll=lambda: SimpleNamespace(caught=True), consume_ball=lambda: self.trainer.remove_item("masterball", 1),
        )
        self.player.ndb.pending_caught_pokemon = []
        instance.battle.execute_item(Action(actor, ActionType.ITEM, foe, item="Master Ball"))
        results = []
        with patch("pokemon.adventures.sessions.resolve_encounter_result", side_effect=lambda _id, _player, result: results.append(result) or AdventureActionResult(True, "saved")):
            instance._handle_battle_result(SimpleNamespace(team="A", player=self.player))
        self.assertEqual(results, ["capture"])
        self.assertEqual(self.trainer.get_item_quantity("masterball"), 0)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from evennia.commands.cmdset import CmdSet
        from evennia.commands.command import Command
        from evennia.objects.models import ObjectDB

        with patch.object(evennia, "Command", Command), patch.object(evennia, "CmdSet", CmdSet):
            from commands.player.cmd_battle_concede import CmdBattleConcede
            from pokemon.adventures.commands import CmdAdventure
        from pokemon.adventures.sessions import AdventureActionResult
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle.engine import Action, ActionType
        from pokemon.battle.handler import battle_handler
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.models.adventures import AdventureSession
        from pokemon.models.core import EncounterPokemon
        from pokemon.models.storage import UserStorage
        from pokemon.models.trainer import Trainer
        from pokemon.services.capture import WildCaptureAttempt

        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AdventureLifecycleCases))
        raise SystemExit(not result.wasSuccessful())

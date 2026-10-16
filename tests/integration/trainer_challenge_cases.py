"""Real NPC challenge startup and retry checks in disposable PostgreSQL."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
from ui_cases import PlayerView


class TrainerChallengeCases(unittest.TestCase):
    """Use real commands, session registration, generated encounters and receipts."""

    def setUp(self):
        """Create one ordinary player and a placed three-member NPC trainer."""
        character = ObjectDB.objects.create(db_key="NPC QA " + uuid4().hex[:8])
        trainer = Trainer.objects.create(user=character, trainer_number=Trainer.objects.count() + 1)
        storage = UserStorage.objects.create(user=character)
        self.player = PlayerView(character, trainer, storage)
        room = ObjectDB.objects.create(db_key="NPC room " + uuid4().hex[:8])
        self.player.location = SimpleNamespace(id=room.pk, key=room.key, name=room.key,
                                               db=room.db, ndb=room.ndb, attributes=room.attributes, contents=[])
        create_owned_pokemon("Squirtle", trainer, 5, ivs=[0] * 6, evs=[0] * 6, active_move_names=["Watergun"])
        npc_trainer = NPCTrainer.objects.create(name="QA trainer " + uuid4().hex[:8])
        for index, species in enumerate(("Rattata", "Pidgey", "Caterpie"), 1):
            NPCPokemonTemplate.objects.create(npc_trainer=npc_trainer, species=species, level=3,
                                              template_key=str(index), sort_order=index,
                                              ivs=[0] * 6, evs=[0] * 6, move_names=["Tackle"])
        npc = ObjectDB.objects.create(db_key=npc_trainer.name)
        ObjectDB.objects.filter(pk=npc.pk).update(db_location=room)
        self.npc = SimpleNamespace(id=npc.pk, pk=npc.pk, key=npc.key, db=npc.db, ndb=npc.ndb,
                                   location=self.player.location)
        self.player.location.contents.append(self.npc)
        self.npc.db.npc_trainer_id = npc_trainer.pk
        self.npc.db.trainer_challenge = {"enabled": True, "cooldown_seconds": 30}
        self.player.search = lambda name, candidates: self.npc

    def tearDown(self):
        """Release only this test's retained session or cleanup receipt."""
        pending = self.player.db.pending_trainer_challenge_cleanup
        if pending:
            self.player.db.battle_lock = pending["battle_id"]
            self.player.db.battle_id = pending["battle_id"]
            retry_trainer_challenge_cleanup(self.player)
        instance = self.player.ndb.battle_instance
        if instance:
            instance.end()

    def command(self, *, retry=False):
        """Invoke the production command boundary with a captured player transport."""
        command = CmdChallenge()
        command.caller = self.player
        command.args = "" if retry else self.npc.key
        command.cmdstring = "+challenge/retry" if retry else "+challenge"
        command.func()

    def room_failure(self):
        """Fail one actual room attribute write inside the session constructor."""
        original = self.player.location.attributes.add
        failed = []

        def add(key, *args, **kwargs):
            if key == "battles" and not failed:
                failed.append(True)
                raise RuntimeError("room registration unavailable")
            return original(key, *args, **kwargs)

        return patch.object(self.player.location.attributes, "add", add)

    def assert_clean(self, before):
        """No failed-start lock, lease, room record or encounter rows may remain."""
        self.assertIsNone(self.player.ndb.battle_instance)
        self.assertIsNone(self.player.db.battle_lock)
        self.assertIsNone(self.player.db.pending_trainer_challenge_cleanup)
        self.assertIsNone(self.npc.db.battle_id)
        self.assertFalse(self.player.location.db.battles)
        self.assertEqual(EncounterPokemon.objects.count(), before)

    def test_normal_start_retains_roster_and_releases_lease(self):
        """The normal player entry point uses all three templates and cleans once."""
        before = EncounterPokemon.objects.count()
        self.command()
        instance = self.player.ndb.battle_instance
        self.assertEqual(len(instance.battle.participants[1].pokemons), 3)
        self.assertEqual(self.npc.db.battle_id, instance.battle_id)
        self.assertEqual(instance.storage.get("encounter")["placed_npc_id"], self.npc.pk)
        instance.end()
        self.assert_clean(before)

    def test_partial_constructor_failure_cleans_and_same_command_can_retry(self):
        """Recover the player reference when constructor assignment never returns."""
        before = EncounterPokemon.objects.count()
        with self.room_failure():
            self.command()
        self.assert_clean(before)
        self.assertIsNone(self.npc.db.trainer_challenge_next_at)
        self.command()
        self.assertTrue(self.player.db.battle_control)

    def test_cleanup_outage_retains_refs_then_retry_command_finishes(self):
        """Temporary storage failure must not erase the pending cleanup identity."""
        before = EncounterPokemon.objects.count()
        with self.room_failure(), patch.object(BattleSession, "end", side_effect=RuntimeError("cleanup unavailable")):
            self.command()
        self.assertEqual(EncounterPokemon.objects.count(), before + 3)
        self.assertTrue(self.player.db.pending_trainer_challenge_cleanup)
        self.assertTrue(any("+challenge/retry" in str(message) for message in self.player.messages))
        self.command(retry=True)
        self.assert_clean(before)

    def test_constructor_cleanup_survives_lost_memory(self):
        """A saved receipt can clear orphaned constructor state after reconnect/reload."""
        before = EncounterPokemon.objects.count()
        with self.room_failure(), patch.object(BattleSession, "end", side_effect=RuntimeError("cleanup unavailable")):
            self.command()
        self.player.ndb.battle_instance = None
        self.command(retry=True)
        self.assert_clean(before)

    def test_late_startup_failure_keeps_npc_reserved_until_retry(self):
        """Protected cleanup must retain a live lease until storage becomes writable."""
        before = EncounterPokemon.objects.count()
        original = BattleSession._setup_battle_room

        def expose_then_fail(instance, **kwargs):
            original(instance, **kwargs)
            raise RuntimeError("late startup failure")

        with patch.object(BattleSession, "_setup_battle_room", expose_then_fail), patch.object(BattleSession, "end", side_effect=RuntimeError("cleanup unavailable")):
            self.command()
        self.assertEqual(self.npc.db.battle_id, self.player.ndb.battle_instance.battle_id)
        self.assertEqual(EncounterPokemon.objects.count(), before + 3)
        self.command(retry=True)
        self.assert_clean(before)

    def test_retry_does_not_clear_another_battle(self):
        """Orphan cleanup refuses a newer player lock and leaves its receipt intact."""
        with self.room_failure(), patch.object(BattleSession, "end", side_effect=RuntimeError("cleanup unavailable")):
            self.command()
        pending = dict(self.player.db.pending_trainer_challenge_cleanup)
        self.player.ndb.battle_instance = None
        self.player.db.battle_lock = "999999"
        self.command(retry=True)
        self.assertEqual(self.player.db.battle_lock, "999999")
        self.assertEqual(dict(self.player.db.pending_trainer_challenge_cleanup), pending)

    def test_late_cleanup_can_restore_saved_session_after_memory_loss(self):
        """A saved startup can be reconstructed before its protected cleanup retry."""
        from pokemon.battle.handler import battle_handler

        before = EncounterPokemon.objects.count()
        original = BattleSession._setup_battle_room

        def expose_then_fail(instance, **kwargs):
            original(instance, **kwargs)
            raise RuntimeError("late startup failure")

        with patch.object(BattleSession, "_setup_battle_room", expose_then_fail), patch.object(BattleSession, "end", side_effect=RuntimeError("cleanup unavailable")):
            self.command()
        instance = self.player.ndb.battle_instance
        battle_handler.unregister(instance)
        self.player.ndb.battle_instance = None
        self.npc.ndb.battle_instance = None
        self.command(retry=True)
        self.assert_clean(before)

    def test_receipt_write_failure_can_retry_from_partial_session(self):
        """A failed receipt write still retains the in-memory cleanup reference."""
        before = EncounterPokemon.objects.count()
        original = self.player.attributes.add

        def fail_receipt(key, *args, **kwargs):
            if key == "pending_trainer_challenge_cleanup":
                raise RuntimeError("receipt unavailable")
            return original(key, *args, **kwargs)

        with self.room_failure(), patch.object(self.player.attributes, "add", fail_receipt):
            self.command()
        self.assertIsNotNone(self.player.ndb.battle_instance)
        self.assertIsNone(self.player.db.pending_trainer_challenge_cleanup)
        self.command(retry=True)
        self.assert_clean(before)

    def test_doubles_require_two_before_allocation(self):
        """A one-member player party cannot reserve or consume a doubles encounter."""
        before = EncounterPokemon.objects.count()
        self.npc.db.trainer_challenge = {"enabled": True, "battle_format": "double"}
        self.command()
        self.assert_clean(before)
        self.assertTrue(any("at least 2 conscious Pokemon" in str(message) for message in self.player.messages))

    def test_doubles_launches_both_active_slots(self):
        """A normal player launches a configured doubles NPC with a full roster."""
        create_owned_pokemon("Eevee", self.player.trainer, 5, ivs=[0] * 6, evs=[0] * 6, active_move_names=["Tackle"])
        self.npc.db.trainer_challenge = {"enabled": True, "battle_format": "double"}
        self.command()
        session = self.player.ndb.battle_instance
        self.assertIsNotNone(session, self.player.messages)
        self.assertEqual([len(part.active) for part in session.battle.participants], [2, 2])
        self.assertEqual(set(session.data.turndata.positions), {"A1", "A2", "B1", "B2"})
        self.assertEqual(len(session.battle.participants[1].pokemons), 3)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from evennia.commands.command import Command
        from evennia.objects.models import ObjectDB

        with patch.object(evennia, "Command", Command):
            from commands.player.cmd_challenge import CmdChallenge
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.models.core import EncounterPokemon
        from pokemon.models.storage import UserStorage
        from pokemon.models.trainer import NPCPokemonTemplate, NPCTrainer, Trainer
        from pokemon.services.trainer_challenges import retry_trainer_challenge_cleanup

        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(TrainerChallengeCases))
        raise SystemExit(not result.wasSuccessful())

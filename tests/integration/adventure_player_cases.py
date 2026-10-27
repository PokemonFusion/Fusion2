"""Ordinary Adventure commands and persisted survey recovery in disposable SQL.

Use actual Evennia character/room models, movement command sets, sessions and
inventory. Only the outbound player transport is captured. No migrations or
running game services are used.
"""

from __future__ import annotations

import json
import os
import random
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres

EVIDENCE = []


class AdventurePlayerCases(unittest.TestCase):
    """Exercise the September survey and retained optional encounter seams."""

    def setUp(self):
        """Create tagged ordinary characters and an existing-pool test fixture."""
        suffix = uuid4().hex[:10]
        self.hall = ObjectDB.objects.create(db_key='Survey Hall ' + suffix,
                                            db_typeclass_path='typeclasses.rooms.Room')
        self.room = ObjectDB.objects.create(db_key='Survey Instance ' + suffix,
                                            db_typeclass_path='typeclasses.rooms.Room')
        self.hall.db.adventure_hall = True
        self.room.db.adventure_instance = True
        self.hall.db.adventure_instance_rooms = [self.room]
        self.player = ObjectDB.objects.create(db_key='Survey Player ' + suffix,
                                              db_typeclass_path='pokemon.user.User')
        self.player.permissions.add('Player')
        self.player.location = self.hall
        self.trainer, _ = Trainer.objects.get_or_create(
            user=self.player, defaults={'trainer_number': Trainer.objects.count() + 1})
        UserStorage.objects.get_or_create(user=self.player)
        self.owned = create_owned_pokemon('Squirtle', self.trainer, 20, nature='Hardy',
                                          ivs=[0] * 6, evs=[0] * 6,
                                          active_move_names=['Tackle', 'Water Gun'])
        self.messages = []
        self.transcript = []
        self.transport = patch.object(self.player, 'msg', side_effect=self.capture)
        self.transport.start()

    def tearDown(self):
        """Release this test's session and retain sanitized command observations."""
        battle = self.player.ndb.battle_instance
        if battle and not getattr(battle, '_ended', False):
            battle.end()
        EVIDENCE.append({'case': self._testMethodName, 'commands': self.transcript,
                         'ordinary_permission': list(self.player.permissions.all()),
                         'no_socket_or_deployment': True})
        self.transport.stop()

    def capture(self, message=None, **kwargs):
        """Capture transport text while leaving all game behavior intact."""
        if message is not None:
            self.messages.append(str(message[0] if isinstance(message, tuple) else message))

    def command(self, text):
        """Run the production slash/cardinal/player command and capture its result."""
        before = len(self.messages)
        sql_before = self.snapshot()
        if text in {'north', 'south'}:
            command = (CmdAdventureNorth if text == 'north' else CmdAdventureSouth)()
            command.args = ''
        elif text.startswith('+adventure/'):
            command = CmdAdventure()
            command.args = '/' + text.split('/', 1)[1]
            command.parse()
        elif text.startswith('+attack '):
            command = CmdBattleAttack()
            command.args = text.split(' ', 1)[1]
            command.parse()
        else:
            raise AssertionError('Unsupported test input ' + text)
        command.caller = self.player
        command.func()
        self.transcript.append({'input': text, 'output': self.messages[before:],
                                'sql_before': sql_before, 'sql_after': self.snapshot()})

    def snapshot(self):
        """Read authoritative session/participation/resource rows for this fixture."""
        sessions = list(AdventureSession.objects.filter(leader=self.player).order_by('pk').values(
            'id', 'state', 'current_node', 'objective_progress', 'metadata'))
        participation = list(AdventureParticipation.objects.filter(player=self.player).order_by('pk').values(
            'session_id', 'route_key', 'encounter_result', 'reward_item', 'reward_amount',
            'completed_at', 'reward_claimed_at'))
        for row in participation:
            row['completed_at'] = row['completed_at'] is not None
            row['reward_claimed_at'] = row['reward_claimed_at'] is not None
        return {'sessions': sessions, 'participation': participation,
                'potions': self.trainer.get_item_quantity('Potion'),
                'battle_lock': self.player.db.battle_lock,
                'player_session': self.player.db.adventure_session_id,
                'room_session': self.room.db.adventure_session_id}

    def start(self):
        """Launch through normal commands and verify canonical persisted pointers."""
        self.command('+adventure/start alpha_meadow')
        session = AdventureSession.objects.get(pk=self.player.db.adventure_session_id)
        self.assertEqual(session.leader_id, self.player.pk)
        self.assertEqual(self.player.location.pk, self.room.pk)
        self.assertEqual(self.room.db.adventure_session_id, session.pk)
        self.assertTrue(self.player.cmdset.has_cmdset(AdventureMovementCmdSet, must_be_default=False))
        return session

    def survey(self, *, from_fork=False):
        """Walk/search/return using actual cardinal command classes."""
        if not from_fork:
            self.command('north')
        self.command('north')
        self.command('+adventure/search')
        self.command('south')
        self.command('south')

    def test_noncombat_commands_resume_complete_leave_and_replay_once(self):
        """A battle-free survey restores its state and grants one first clear only."""
        self.command('+adventure/list')
        self.command('+adventure/info alpha_meadow')
        session = self.start()
        self.command('north')
        detach_movement_cmdset(self.player)
        restored = sync_player_to_active_session(ObjectDB.objects.get(pk=self.player.pk))
        self.assertEqual(restored.pk, session.pk)
        self.assertEqual(restored.current_node, 'tall_grass')
        self.command('+adventure/look')
        self.survey(from_fork=True)
        session.refresh_from_db()
        self.assertEqual(session.state, 'completed')
        self.assertEqual(session.objective_progress['resolve_encounter'], 0)
        self.assertFalse(session.metadata.get('encounter_state'))
        participation = AdventureParticipation.objects.get(session=session, player=self.player)
        self.assertIsNotNone(participation.completed_at)
        self.assertIsNotNone(participation.reward_claimed_at)
        self.assertEqual(participation.encounter_result, '')
        self.assertEqual(self.trainer.get_item_quantity('Potion'), 1)
        self.assertIsNone(self.player.ndb.battle_instance)
        self.assertEqual(EncounterPokemon.objects.count(), 0)
        self.command('+adventure/objectives')
        self.command('+adventure/leave')
        self.assertEqual(self.player.location.pk, self.hall.pk)
        self.assertFalse(self.player.db.adventure_session_id)
        self.assertFalse(self.room.db.adventure_session_id)
        self.assertFalse(self.player.cmdset.has_cmdset(AdventureMovementCmdSet, must_be_default=False))
        self.start()
        self.survey()
        self.command('+adventure/leave')
        self.command('+adventure/claim')
        self.command('+adventure/claim')
        self.assertEqual(self.trainer.get_item_quantity('Potion'), 1)

    def test_no_search_no_clear_and_abandon_releases_instance(self):
        """Walking home cannot skip the survey and leaving permits a fresh run."""
        session = self.start()
        for direction in ('north', 'north', 'south', 'south'):
            self.command(direction)
        session.refresh_from_db()
        self.assertEqual(session.state, 'active')
        self.assertEqual(self.trainer.get_item_quantity('Potion'), 0)
        self.command('+adventure/leave')
        session.refresh_from_db()
        self.assertEqual(session.state, 'abandoned')
        self.assertFalse(self.room.db.adventure_session_id)
        self.assertNotEqual(self.start().pk, session.pk)

    def test_expired_session_releases_only_its_pointers(self):
        """Fresh SQL expiry leaves no live room reservation or claimable reward."""
        session = self.start()
        AdventureSession.objects.filter(pk=session.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertIsNone(sync_player_to_active_session(self.player))
        session.refresh_from_db()
        self.assertEqual(session.state, 'expired')
        self.assertFalse(self.player.db.adventure_session_id)
        self.assertFalse(self.room.db.adventure_session_id)
        self.command('+adventure/claim')
        self.assertEqual(self.trainer.get_item_quantity('Potion'), 0)

    def test_reward_write_failure_recovers_after_leave_without_duplication(self):
        """An actual inventory write rolls back and ordinary claims recover once."""
        session = self.start()
        original = Trainer.add_item

        def fail_after_write(trainer, name, amount=1):
            original(trainer, name, amount)
            raise RuntimeError('controlled disposable survey reward fault')

        with patch.object(Trainer, 'add_item', fail_after_write):
            self.survey()
            self.command('+adventure/claim')
        self.assertEqual(self.trainer.get_item_quantity('Potion'), 0)
        self.assertIsNone(AdventureParticipation.objects.get(session=session).reward_claimed_at)
        self.command('+adventure/leave')
        self.command('+adventure/claim')
        self.command('+adventure/claim')
        self.assertEqual(self.trainer.get_item_quantity('Potion'), 1)
        self.assertIsNotNone(AdventureParticipation.objects.get(session=session).reward_claimed_at)

    def test_real_wild_command_win_records_result_and_keeps_survey(self):
        """Retain the existing optional battle route through real command turns."""
        session = self.start()
        self.command('north')
        self.command('+adventure/choose wild')
        battle = self.player.ndb.battle_instance
        self.assertIsNotNone(battle, self.messages[-5:])
        battle.battle.rng = random.Random(2)
        for _ in range(20):
            if getattr(battle, '_ended', False):
                break
            self.command('+attack Water Gun')
            self.assertFalse(battle.turn_state.get('error'), battle.turn_state)
        self.assertTrue(getattr(battle, '_ended', False), self.messages[-10:])
        session.refresh_from_db()
        self.assertEqual(session.metadata['encounter_result'], 'win')
        self.assertEqual(AdventureParticipation.objects.get(session=session).encounter_result, 'win')
        self.survey(from_fork=True)
        self.command('+adventure/leave')
        self.assertEqual(self.trainer.get_item_quantity('Potion'), 1)
        self.assertFalse(self.player.db.battle_lock)
        self.assertFalse(self.room.db.battles)

    def test_selected_route_cannot_bypass_pending_result_then_retry(self):
        """Real route state blocks a battle-free clear until the retained outcome saves."""
        session = self.start()
        self.command('north')
        # Commit the same production selection seam used before battle allocation.
        result = choose_session_route(self.player, 'trainer')
        self.assertTrue(result.ok)
        self.survey(from_fork=True)
        session.refresh_from_db()
        self.assertEqual(session.state, 'active')
        self.assertEqual(self.trainer.get_item_quantity('Potion'), 0)
        queue_encounter_result(session.pk, self.player, 'loss')
        self.command('+adventure/retry')
        session.refresh_from_db()
        self.assertEqual(session.state, 'completed')
        self.assertEqual(session.metadata['encounter_result'], 'loss')
        self.command('+adventure/retry')
        self.command('+adventure/claim')
        self.assertFalse(self.player.db.pending_adventure_results)
        self.assertEqual(self.trainer.get_item_quantity('Potion'), 1)


if __name__ == '__main__':
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from django.apps import apps
        from django.contrib.contenttypes.models import ContentType
        from django.utils import timezone
        from evennia.commands.cmdset import CmdSet
        from evennia.commands.command import Command
        from evennia.objects.models import ObjectDB
        from evennia.utils.search import search_object
        # Model tables are created without migrations, so bootstrap the real
        # content-type registry required to serialize room/object references.
        ContentType.objects.get_for_models(*apps.get_models(), for_concrete_models=False)
        evennia.search_object = search_object
        with patch.object(evennia, 'Command', Command), patch.object(evennia, 'CmdSet', CmdSet):
            from commands.player.cmd_battle_attack import CmdBattleAttack
            from pokemon.adventures.cmdsets import (
                AdventureMovementCmdSet,
                CmdAdventureNorth,
                CmdAdventureSouth,
                detach_movement_cmdset,
            )
            from pokemon.adventures.commands import CmdAdventure
        from pokemon.adventures.sessions import (
            choose_session_route,
            queue_encounter_result,
            sync_player_to_active_session,
        )
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.models.adventures import AdventureParticipation, AdventureSession
        from pokemon.models.core import EncounterPokemon
        from pokemon.models.storage import UserStorage
        from pokemon.models.trainer import Trainer

        result = unittest.TextTestRunner(verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(AdventurePlayerCases))
        if path := os.environ.get('PF2_ADVENTURE_PLAYER_EVIDENCE'):
            Path(path).write_text(json.dumps({'passed': result.wasSuccessful(), 'cases': EVIDENCE},
                                            indent=2) + '\n', encoding='utf-8')
        raise SystemExit(not result.wasSuccessful())

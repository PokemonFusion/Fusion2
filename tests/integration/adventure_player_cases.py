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

    def test_leave_after_expiry_removes_stale_cardinal_commands(self):
        """An ended run does not retain cardinal overrides over normal room exits."""
        session = self.start()
        AdventureSession.objects.filter(pk=session.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1))

        self.command('+adventure/leave')

        session.refresh_from_db()
        self.assertEqual(session.state, 'expired')
        self.assertFalse(self.player.db.adventure_session_id)
        self.assertFalse(self.room.db.adventure_session_id)
        self.assertFalse(self.player.cmdset.has_cmdset(AdventureMovementCmdSet, must_be_default=False))

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
        self.assertEqual(session.state, 'active')
        self.assertEqual(session.metadata['encounter_result'], 'loss')
        self.survey(from_fork=True)
        session.refresh_from_db()
        self.assertEqual(session.state, 'completed')
        self.command('+adventure/retry')
        self.command('+adventure/claim')
        self.assertFalse(self.player.db.pending_adventure_results)
        self.assertEqual(self.trainer.get_item_quantity('Potion'), 1)

    def assert_encounter_blocks_commands(self, route):
        """Run real player actions during an authored wild or NPC battle."""
        session = self.start()
        self.command('north')
        self.command('+adventure/choose ' + route)
        battle = self.player.ndb.battle_instance
        self.assertIsNotNone(battle, self.messages[-5:])
        before = self.snapshot()
        for command in ('north', '+adventure/search', '+adventure/choose ' + route,
                        '+adventure/start alpha_meadow', '+adventure/leave'):
            self.command(command)
            self.assertEqual(self.snapshot(), before, command)
        detach_movement_cmdset(self.player)
        self.command('+adventure/look')
        self.command('+adventure/objectives')
        self.assertTrue(self.player.cmdset.has_cmdset(AdventureMovementCmdSet, must_be_default=False))
        self.assertEqual(self.player.location.pk, self.room.pk)
        self.assertEqual(AdventureSession.objects.filter(leader=self.player).count(), 1)

    def test_wild_battle_blocks_production_adventure_commands(self):
        """An ordinary player's active wild battle blocks each lifecycle action."""
        self.assert_encounter_blocks_commands('wild')

    def test_trainer_battle_blocks_production_adventure_commands(self):
        """An ordinary player's active NPC battle has the same action gates."""
        self.assert_encounter_blocks_commands('trainer')

    def test_registry_and_marker_loss_preserves_storage_then_reconnect(self):
        """Persistent room parts protect the run through cleanup and reconnect."""
        from pokemon.battle.handler import battle_handler
        from world.stale_state import cleanup_stale_state

        session = self.start()
        self.command('north')
        self.command('+adventure/choose wild')
        battle = self.player.ndb.battle_instance
        self.assertIsNotNone(battle)
        original_data = battle.storage.get('data')
        original_hp = self.owned.current_hp
        original_pp = list(self.owned.activemoveslot_set.order_by('slot').values_list('current_pp', flat=True))
        original_encounters = list(EncounterPokemon.objects.order_by('pk').values_list('pk', flat=True))
        AdventureSession.objects.filter(pk=session.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1))
        self.player.ndb.battle_instance = None
        self.player.db.adventure_session_id = None
        self.room.db.adventure_session_id = None
        self.room.db.battles = []
        self.room.ndb.battle_instances = {}
        battle_handler.unregister(battle)
        outside = ObjectDB.objects.create(db_key='Reconnect ' + uuid4().hex[:8])
        # Simulate a persisted reconnect location without invoking movement.
        self.player.db_location = outside
        self.player.save(update_fields=['db_location'])
        counts = cleanup_stale_state(objects=[self.player, self.room], active_battle_ids=set())
        self.assertFalse(any(counts.values()), counts)
        self.assertEqual(battle.storage.get('data'), original_data)
        restored = sync_player_to_active_session(ObjectDB.objects.get(pk=self.player.pk))
        self.assertEqual(restored.pk, session.pk)
        resumed = BattleSession.ensure_for_player(self.player)
        self.assertIsNotNone(resumed)
        self.assertEqual(resumed.battle_id, battle.battle_id)
        self.assertEqual(resumed.room.pk, self.room.pk)
        self.assertEqual(resumed.captainA.pk, self.player.pk)
        self.assertIs(battle_handler.get(battle.battle_id), resumed)
        self.assertEqual(list(EncounterPokemon.objects.order_by('pk').values_list('pk', flat=True)), original_encounters)
        self.assertEqual(self.player.location.pk, outside.pk)
        self.owned.refresh_from_db()
        self.assertEqual(self.owned.current_hp, original_hp)
        self.assertEqual(list(self.owned.activemoveslot_set.order_by('slot').values_list('current_pp', flat=True)), original_pp)
        self.command('north')
        self.command('+adventure/leave')
        session.refresh_from_db()
        self.assertEqual(session.state, 'active')
        resumed.battle.rng = random.Random(2)
        for _ in range(20):
            if getattr(resumed, '_ended', False):
                break
            self.command('+attack Water Gun')
        self.assertTrue(getattr(resumed, '_ended', False), self.messages[-10:])
        session.refresh_from_db()
        self.assertEqual(session.metadata['encounter_result'], 'win')
        self.assertEqual(AdventureParticipation.objects.get(session=session).encounter_result, 'win')
        self.assertFalse(self.player.db.battle_lock)
        self.assertEqual(self.player.location.pk, outside.pk)
        self.assertIsNone(sync_player_to_active_session(self.player))
        self.assertEqual(AdventureSession.objects.filter(leader=self.player).count(), 1)

    def test_retry_restores_original_terminal_battle_from_outside(self):
        """A retained result remains player-recoverable with no runtime or battle ID."""
        from pokemon.battle.handler import battle_handler

        session = self.start()
        self.command('north')
        self.command('+adventure/choose wild')
        battle = self.player.ndb.battle_instance
        concede = CmdBattleConcede()
        concede.caller = self.player
        with patch('pokemon.adventures.sessions.queue_encounter_result', side_effect=RuntimeError('receipt outage')):
            concede._finalize_concession(battle, battle_handler)
        self.assertEqual(battle._adventure_result, 'loss')
        battle_handler.unregister(battle)
        self.room.ndb.battle_instances = {}
        self.player.ndb.battle_instance = None
        self.player.db.battle_id = None
        outside = ObjectDB.objects.create(db_key='Terminal reconnect ' + uuid4().hex[:8])
        self.player.db_location = outside
        self.player.save(update_fields=['db_location'])

        self.command('+adventure/retry')

        session.refresh_from_db()
        self.assertEqual(session.metadata['encounter_result'], 'loss')
        self.assertEqual(AdventureParticipation.objects.get(session=session).encounter_result, 'loss')
        self.assertFalse(self.player.db.battle_lock)
        self.assertFalse(self.player.db.pending_adventure_results)
        self.assertIsNone(getattr(self.room.db, f'battle_{battle.battle_id}_data'))
        self.assertFalse(self.room.db.battles)
        self.assertIsNone(battle_handler.get(battle.battle_id))
        self.assertEqual(self.player.location.pk, outside.pk)
        once = self.snapshot()
        self.command('+adventure/retry')
        self.assertEqual(self.snapshot(), once)

    def assert_reconnected_movement_resumes(self, pending_result):
        """Reconnect during combat, then resume cardinal input without another look."""
        from evennia.objects.objects import DefaultCharacter
        from pokemon.adventures.sessions import AdventureActionResult
        from pokemon.battle.handler import battle_handler

        session = self.start()
        self.command('north')
        self.command('+adventure/choose wild')
        battle = self.player.ndb.battle_instance
        battle_handler.unregister(battle)
        self.player.ndb.battle_instance = None
        self.room.ndb.battle_instances = {}
        detach_movement_cmdset(self.player)
        # Only the framework socket/puppet setup is omitted. Run the real PF2
        # reconnect hook, battle rehydration, cmdsets and production commands.
        with patch.object(DefaultCharacter, 'at_post_puppet', return_value=None):
            self.player.at_post_puppet()
        resumed = self.player.ndb.battle_instance
        self.assertIsNotNone(resumed)
        self.assertTrue(self.player.cmdset.has_cmdset(AdventureMovementCmdSet, must_be_default=False))
        self.command('north')
        session.refresh_from_db()
        self.assertEqual(session.current_node, 'tall_grass')
        concede = CmdBattleConcede()
        concede.caller = self.player
        if pending_result:
            with patch('pokemon.adventures.sessions.resolve_encounter_result',
                       return_value=AdventureActionResult(False, 'controlled result outage')):
                concede._finalize_concession(resumed, battle_handler)
            self.command('north')
            session.refresh_from_db()
            self.assertEqual(session.current_node, 'tall_grass')
            self.command('+adventure/retry')
        else:
            concede._finalize_concession(resumed, battle_handler)
        self.assertFalse(self.player.db.battle_lock)
        self.survey(from_fork=True)
        session.refresh_from_db()
        self.assertEqual(session.state, 'completed')
        self.command('+adventure/leave')
        self.assertEqual(self.player.location.pk, self.hall.pk)
        self.assertEqual(self.trainer.get_item_quantity('Potion'), 1)

    def test_reconnected_battle_resumes_cardinals_after_cleanup(self):
        """A reconnecting player continues the survey as soon as combat ends."""
        self.assert_reconnected_movement_resumes(False)

    def test_reconnected_pending_result_resumes_cardinals_after_retry(self):
        """Pending receipt recovery unlocks the already installed cardinal commands."""
        self.assert_reconnected_movement_resumes(True)

    def test_expired_pending_outcome_retries_once_without_replacement(self):
        """Terminal cleanup preserves an expired run's original outcome receipt."""
        from pokemon.adventures.sessions import AdventureActionResult, expire_session
        from pokemon.battle.handler import battle_handler
        from world.stale_state import cleanup_stale_state

        session = self.start()
        self.command('north')
        self.command('+adventure/choose wild')
        battle = self.player.ndb.battle_instance
        command = CmdBattleConcede()
        command.caller = self.player
        with patch('pokemon.adventures.sessions.resolve_encounter_result',
                   return_value=AdventureActionResult(False, 'controlled result outage')):
            command._finalize_concession(battle, battle_handler)
        self.assertIsNone(self.player.ndb.battle_instance)
        self.assertEqual(dict(self.player.db.pending_adventure_results), {str(session.pk): 'loss'})
        AdventureSession.objects.filter(pk=session.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1))
        cleanup_stale_state(objects=[self.player, self.room], active_battle_ids=set())
        before = self.snapshot()
        for text in ('north', '+adventure/search', '+adventure/choose wild',
                     '+adventure/start alpha_meadow', '+adventure/leave'):
            self.command(text)
            self.assertEqual(self.snapshot(), before, text)
        self.command('+adventure/retry')
        once = self.snapshot()
        self.command('+adventure/retry')
        self.assertEqual(self.snapshot(), once)
        session.refresh_from_db()
        self.assertEqual(session.metadata['encounter_result'], 'loss')
        self.assertEqual(AdventureParticipation.objects.get(session=session).encounter_result, 'loss')
        self.assertFalse(self.player.db.pending_adventure_results)
        self.assertTrue(expire_session(session))
        self.assertFalse(self.player.db.adventure_session_id)
        self.assertFalse(self.room.db.adventure_session_id)
        self.assertEqual(AdventureSession.objects.filter(leader=self.player).count(), 1)

    def test_administrative_return_and_abort_preserve_active_battle(self):
        """Staff cleanup respects battle evidence; ordinary players lack access."""
        self.start()
        self.command('north')
        self.command('+adventure/choose wild')
        staff = ObjectDB.objects.create(db_key='Adventure Staff ' + uuid4().hex[:8],
                                        db_typeclass_path='pokemon.user.User')
        staff.permissions.add('Wizards')
        command = CmdAdventureAdmin()
        command.caller = staff
        self.assertFalse(command.access(self.player, 'cmd'))
        self.assertTrue(command.access(staff, 'cmd'))
        output = []
        before = self.snapshot()
        with patch.object(staff, 'msg', side_effect=output.append), \
                patch.object(staff, 'search', return_value=self.player):
            command._abort(str(self.player.db.adventure_session_id))
            command._return_player(self.player.key)
        self.assertEqual(len(output), 2)
        self.assertTrue(all('must finish' in str(message) for message in output))
        self.assertEqual(self.snapshot(), before)

    def test_rejected_return_keeps_session_and_movement_until_success(self):
        """A failed physical return cannot strand an abandoned, unowned player."""
        session = self.start()
        before = self.snapshot()
        with patch.object(self.player, 'move_to', return_value=False):
            self.command('+adventure/leave')
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.player.location.pk, self.room.pk)
        self.assertTrue(self.player.cmdset.has_cmdset(AdventureMovementCmdSet, must_be_default=False))
        self.command('+adventure/leave')
        session.refresh_from_db()
        self.assertEqual(session.state, 'abandoned')
        self.assertEqual(self.player.location.pk, self.hall.pk)

    def test_old_expiry_keeps_newer_persisted_session_markers(self):
        """An old terminal operation never releases the replacement run."""
        from pokemon.adventures.sessions import expire_session

        old = self.start()
        old.state = 'abandoned'
        old.save(update_fields=['state'])
        replacement = AdventureSession.objects.create(
            leader=self.player, instance_room=self.room, return_location=self.hall,
            template_key='alpha_meadow', current_node='entrance')
        self.player.db.adventure_session_id = self.room.db.adventure_session_id = replacement.pk

        self.assertTrue(expire_session(old))

        self.assertEqual(self.player.db.adventure_session_id, replacement.pk)
        self.assertEqual(self.room.db.adventure_session_id, replacement.pk)
        self.command('+adventure/look')
        replacement.refresh_from_db()
        self.assertEqual(replacement.state, 'active')


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
            from commands.admin.cmd_adventureadmin import CmdAdventureAdmin
            from commands.player.cmd_battle_attack import CmdBattleAttack
            from commands.player.cmd_battle_concede import CmdBattleConcede
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
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle import battleinstance
        # Bind the actual standalone search API used to rehydrate controllers.
        # The optional-runtime compatibility module can have imported earlier.
        battleinstance.search_object = search_object

        result = unittest.TextTestRunner(verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(AdventurePlayerCases))
        if path := os.environ.get('PF2_ADVENTURE_PLAYER_EVIDENCE'):
            Path(path).write_text(json.dumps({'passed': result.wasSuccessful(), 'cases': EVIDENCE},
                                            indent=2) + '\n', encoding='utf-8')
        raise SystemExit(not result.wasSuccessful())

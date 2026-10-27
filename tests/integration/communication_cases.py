"""Actual mail/board state, player permissions, independent recipients and sessions."""

from io import StringIO
import json
import os
from pathlib import Path
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
from ordinary_player_fixtures import OrdinaryPlayerFixtures

TRANSCRIPT = []


class CommunicationCases(unittest.TestCase):
    """Keep state in actual Evennia Msg, tags and Script Attributes; capture transport."""

    def setUp(self):
        """Give each case two ordinary accounts and a same-account alternate."""
        self.player = fixtures.character()
        self.other = fixtures.character()
        self.alt = fixtures.character(account=self.player.account)
        self.players = (self.player, self.other, self.alt)
        self.messages, self.steps, self.transports = {}, [], []
        for player in self.players:
            self.assertEqual(set(player.permissions.all()), {'player'})
            self.assertFalse(player.account.is_superuser)
            self.messages[player.pk] = []
            capture = patch.object(player, 'msg', side_effect=lambda text=None, _id=player.pk, **kwargs: self.messages[_id].append(text))
            capture.start()
            self.transports.append(capture)
        self.board = create_script(typeclass=BBoard, key='Comms QA ' + uuid4().hex[:8], autostart=False)
        self.board.tags.add('october-communication-qa')

    def tearDown(self):
        """Persist labelled ordinary command evidence without contacting real players."""
        for capture in self.transports:
            capture.stop()
        TRANSCRIPT.append({'case': self._testMethodName, 'commands': self.steps,
            'ordinary_permissions': [list(player.permissions.all()) for player in self.players],
            'transport': 'captured; no live socket', 'staff_setup': 'separate tagged fixture only when explicitly used'})

    def test_raw_slash_mail_parser_send_read_reply_and_archive(self):
        """Real MUX parsing must work before the production mail methods run."""
        def execute(actor, arguments):
            """Supply raw dispatcher arguments without prefilled switches/lhs/rhs."""
            command = CmdMail()
            command.caller, command.args = actor, arguments
            command.cmdstring, command.raw_string = '+mail', '+mail' + arguments
            start = len(self.messages[actor.pk])
            command.parse()
            command.func()
            output = self.messages[actor.pk][start:]
            self.steps.append({'character': actor.pk, 'input': '+mail' + arguments, 'output': output})
            return str(output)
        self.assertIn('sent to', execute(self.player, '/send ' + self.other.key + '=Raw parser/Live route regression'))
        message = mail.list_character_mail(self.other)[0]
        self.assertIn('Live route regression', execute(self.other, '/read ' + str(message.pk)))
        self.assertIn('Reply sent', execute(self.other, '/reply ' + str(message.pk) + '=Raw reply'))
        self.assertIn('archived', execute(self.other, '/delete ' + str(message.pk)))
        self.assertFalse(mail.list_character_mail(self.other))
        self.assertEqual(mail.mail_body(mail.list_character_mail(self.player)[0]), 'Raw reply')

    def test_board_subject_free_text_opens_real_editor_and_saves_one_post(self):
        """Exercise the actual menu dispatcher instead of calling a node directly."""
        from bboard.commands import CmdBBPost
        command = CmdBBPost()
        command.caller, command.args = self.player, self.board.key
        command.func()
        menu = self.player.ndb._evmenu
        self.assertIsNotNone(menu)
        with patch.object(self.player, 'execute_cmd', wraps=self.player.execute_cmd) as dispatch:
            menu.parse_input('Normal subject with spaces')
        dispatch.assert_not_called()
        editor = self.player.ndb._eveditor
        self.assertIsNotNone(editor, self.messages[self.player.pk])
        self.assertEqual(editor.get_buffer(), '')
        editor.update_buffer('Normal editor body')
        editor.save_buffer()
        self.assertFalse(editor._unsaved)
        editor.update_buffer('A second save must not create another post')
        editor.save_buffer()
        self.assertIn('already saved', str(self.messages[self.player.pk]))
        editor.quit()
        posts = self.board.posts()
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]['subject'], 'Normal subject with spaces')
        self.assertEqual(posts[0]['body'], 'Normal editor body')
        self.assertNotIn('Post aborted', str(self.messages[self.player.pk]))
        self.steps.append({'character': self.player.pk, 'input': '+bbpost / free subject / editor body / save',
                           'output': self.messages[self.player.pk]})

    def mail(self, actor, action='', *, args='', lhs='', rhs=''):
        """Execute the actual registered character mail command."""
        start = len(self.messages[actor.pk])
        command = CmdMail()
        command.caller, command.args, command.switches = actor, args, [action] if action else []
        command.lhs, command.rhs = lhs, rhs
        command.func()
        self.steps.append({'character': actor.pk, 'input': '+mail' + ('/' + action if action else '') + ' ' + (f'{lhs}={rhs}' if lhs else args),
            'output': self.messages[actor.pk][start:]})
        return self.messages[actor.pk][-1]

    def board_command(self, actor, kind, args):
        """Execute registered board commands against actual persisted boards and locks."""
        start = len(self.messages[actor.pk])
        command = kind()
        command.caller, command.args = actor, args
        command.func()
        self.steps.append({'character': actor.pk, 'input': command.key + ' ' + args, 'output': self.messages[actor.pk][start:]})
        return self.messages[actor.pk][-1]

    def shared(self):
        """Set up legacy/shared mail explicitly, separate from ordinary single-target sends."""
        return create_message(self.player, 'Shared private QA body', receivers=[self.other, self.alt], header='Shared QA',
            tags=[(mail.MAIL_TAG, mail.MAIL_CATEGORY), (mail.UNREAD_TAG, mail.MAIL_CATEGORY)])

    def race(self, *actions):
        """Prove competing operations use independent PostgreSQL connections."""
        barrier = Barrier(len(actions))
        def worker(action):
            """Never leak a test connection beyond the child operation."""
            try:
                connection.ensure_connection()
                with connection.cursor() as cursor:
                    cursor.execute('SELECT pg_backend_pid()')
                    pid = cursor.fetchone()[0]
                barrier.wait(timeout=10)
                return pid, action()
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            results = list(pool.map(worker, actions))
        self.assertEqual(len({row[0] for row in results}), len(actions))
        return [row[1] for row in results]

    def test_actual_user_lookup_send_read_reply_archive_and_reconnect(self):
        """The normal lookup includes pokemon.user.User and keeps two alts independent."""
        before = Msg.objects.count()
        self.assertIn('sent to', self.mail(self.player, 'send', lhs=self.other.key, rhs='QA subject/QA body'))
        self.assertEqual(Msg.objects.count(), before + 1)
        message = mail.list_character_mail(self.other)[0]
        self.assertEqual((mail.unread_mail_count(self.other), mail.unread_mail_count(self.alt)), (1, 0))
        self.assertIn('QA body', self.mail(self.other, 'read', args=str(message.pk)))
        self.other.attributes.reset_cache()
        self.assertEqual(mail.unread_mail_count(self.other), 0)
        self.assertIn('Reply sent', self.mail(self.other, 'reply', lhs=str(message.pk), rhs='QA reply'))
        reply = mail.list_character_mail(self.player)[0]
        self.assertEqual(mail.mail_body(reply), 'QA reply')
        self.assertIn('archived', self.mail(self.other, 'delete', args=str(message.pk)))
        self.assertIn('No mail', self.mail(self.other, 'read', args=str(message.pk)))
        self.assertIn('No mail', self.mail(self.other, 'delete', args=str(message.pk)))
        self.assertTrue(Msg.objects.filter(pk=message.pk).exists())

    def test_shared_mail_read_unread_and_archive_change_only_that_recipient(self):
        """Legacy shared messages gain independent state without inventing prior history."""
        message = self.shared()
        self.mail(self.other, 'read', args=str(message.pk))
        self.assertEqual((mail.unread_mail_count(self.other), mail.unread_mail_count(self.alt)), (0, 1))
        self.mail(self.other, 'unread', args=str(message.pk))
        self.assertEqual((mail.unread_mail_count(self.other), mail.unread_mail_count(self.alt)), (1, 1))
        self.mail(self.other, 'delete', args=str(message.pk))
        self.assertEqual(mail.unread_mail_count(self.alt), 1)
        self.assertIn('Shared private QA body', self.mail(self.alt, 'read', args=str(message.pk)))
        self.assertEqual(mail.unread_mail_count(self.alt), 0)

    def test_foreign_ids_account_actor_and_sender_spoofing_fail_through_commands(self):
        """Same-account membership never makes another character's inbox private state shared."""
        message = mail.send_character_mail(self.other, self.player, 'Private', 'Never expose to alt')
        for actor in (self.alt, self.other):
            for action in ('read', 'unread', 'delete'):
                self.assertIn('No mail', self.mail(actor, action, args=str(message.pk)))
            self.assertIn('No mail', self.mail(actor, 'reply', lhs=str(message.pk), rhs='forged reply'))
        self.assertEqual(mail.unread_mail_count(self.player), 1)
        with self.assertRaises(mail.CharacterMailError):
            mail.read_character_mail(self.player.account, message.pk)
        account_output = []
        command = CmdMail()
        command.caller, command.args, command.switches = self.player.account, '', ['send']
        command.lhs, command.rhs = self.alt.key, 'Spoof/No'
        with patch.object(self.player.account, 'msg', side_effect=account_output.append):
            command.func()
        self.assertIn('active character', account_output[-1])

    def test_independent_connections_read_shared_mail_without_lost_state(self):
        """Two simultaneous recipient reads each commit exactly their own state."""
        message = self.shared()
        self.assertTrue(mail.is_unread(message, self.other))
        results = self.race(lambda: mail.read_character_mail(self.other, message.pk).pk,
            lambda: mail.read_character_mail(self.alt, message.pk).pk)
        self.assertEqual(results, [message.pk, message.pk])
        self.assertFalse(mail.is_unread(message, self.other))
        self.assertFalse(mail.is_unread(message, self.alt))
        self.assertEqual(mail.unread_mail_counts_for_characters([self.player, self.alt]), {})

    def test_reply_failure_rolls_back_new_message_and_original_read_state(self):
        """A fault after real reply/receiver/tag writes cannot consume the unread state."""
        message = mail.send_character_mail(self.player, self.other, 'Original', 'body')
        before = Msg.objects.count()
        original = mail._create_message
        def fail_after_send(*args, **kwargs):
            """Keep all actual message and receiver writes before the injected fault."""
            original(*args, **kwargs)
            raise RuntimeError('injected reply save failure')
        with patch.object(mail, '_create_message', fail_after_send), self.assertRaises(RuntimeError):
            mail.reply_to_character_mail(self.other, message.pk, 'reply')
        self.assertEqual(Msg.objects.count(), before)
        self.assertTrue(mail.is_unread(message, self.other))
        with self.assertRaises(mail.CharacterMailError):
            mail.reply_to_character_mail(self.other, message.pk, '')
        self.assertTrue(mail.is_unread(message, self.other))

    def test_saved_send_survives_notification_transport_failure(self):
        """Durable delivery and immediate notification have separate success semantics."""
        with patch.object(self.other, 'msg', side_effect=RuntimeError('injected transport failure')):
            message = mail.send_character_mail(self.player, self.other, 'Saved', 'still in inbox')
        self.assertTrue(Msg.objects.filter(pk=message.pk).exists())
        self.assertEqual(mail.unread_mail_count(self.other), 1)

    def test_board_persisted_saver_mapping_reconnect_and_independent_readers(self):
        """Real serialized read maps remain effective after cache discard."""
        self.board.post('First', 'First board body', self.player)
        self.board.post('Second', 'Second board body', self.player)
        self.assertEqual(self.board.unread_count(self.player), 0)
        self.assertEqual(self.board.unread_count(self.other), 2)
        self.board_command(self.other, CmdBBRead, self.board.key + '/1')
        self.board.attributes.reset_cache()
        self.assertTrue(self.board.has_read(self.other, 1))
        self.assertFalse(self.board.has_read(self.alt, 1))
        self.race(lambda: self.board.mark_read(self.other, 2), lambda: self.board.mark_read(self.alt, 1))
        self.assertEqual((self.board.unread_count(self.other), self.board.unread_count(self.alt)), (0, 1))
        self.board_command(self.alt, CmdBBList, '')
        self.board_command(self.alt, CmdBBCatchup, str(_board_number(self.alt, self.board)))
        self.assertEqual(self.board.unread_count(self.alt), 0)

    def test_board_private_access_and_foreign_delete_do_not_change_state(self):
        """Invisible boards and another author's post cannot be read or deleted."""
        self.board.post('Owned', 'Private body when locked', self.player)
        self.assertIn('permission', self.board_command(self.other, CmdBBDelete, self.board.key + '/1'))
        self.assertEqual(self.board.num_posts(), 1)
        self.board.locks.add('read:perm(Admin);post:perm(Admin);delete:perm(Admin);edit:perm(Admin)')
        output = self.board_command(self.other, CmdBBRead, self.board.key + '/1')
        self.assertNotIn('Private body when locked', output)
        with self.assertRaises(BoardError):
            self.board.mark_read(self.other, 1)

    def test_board_new_post_never_reuses_deleted_read_identity_at_same_clock_tick(self):
        """Stable post IDs remain unique even when time and list index are repeated."""
        import datetime
        fixed = datetime.datetime(2026, 10, 23, 12, 0)
        clock = SimpleNamespace(datetime=SimpleNamespace(utcnow=lambda: fixed))
        with patch('bboard.bboard.datetime', clock):
            self.board.post('Old', 'old', self.player)
            old_id = self.board.get_post(1)['id']
            self.board.mark_read(self.other, 1)
            self.board.delete_post(1)
            self.board.post('New', 'new', self.player)
        self.assertNotEqual(self.board.get_post(1)['id'], old_id)
        self.assertFalse(self.board.has_read(self.other, 1))

    def test_board_unread_scan_does_not_repeat_database_locks_for_every_helper(self):
        """One board operation retains its lock/cache across nested per-post helpers."""
        from django.test.utils import CaptureQueriesContext
        for index in range(20):
            self.board.post('Post ' + str(index), 'body', self.player)
        with CaptureQueriesContext(connection) as captured:
            self.assertEqual(self.board.unread_count(self.other), 20)
        self.assertLess(len(captured), 200, f'Nested board helpers issued {len(captured)} queries for 20 posts')

    def test_board_concurrent_posts_and_rollback_preserve_existing_rows(self):
        """Posts/read maps serialize and a later attribute failure rolls back together."""
        self.race(lambda: self.board.post('A', 'body A', self.player), lambda: self.board.post('B', 'body B', self.other))
        self.assertEqual(self.board.num_posts(), 2)
        self.assertEqual(len({row['id'] for row in self.board.posts()}), 2)
        before = [dict(row) for row in self.board.posts()]
        original = Attribute.save
        def fail_tracking(row, *args, **kwargs):
            """Fail after the real read-map save following a real post-list save."""
            result = original(row, *args, **kwargs)
            if row.db_key == 'read_tracking':
                raise RuntimeError('injected board tracking write failure')
            return result
        with patch.object(Attribute, 'save', fail_tracking), self.assertRaises(RuntimeError):
            self.board.post('Failed', 'must roll back', self.alt)
        self.assertEqual([dict(row) for row in self.board.posts()], before)

    def test_editor_rechecks_access_and_stable_post_identity_before_saving(self):
        """A separate staff editor cannot overwrite a different post after renumbering."""
        staff = fixtures.character(staff=True)
        self.board.post('First', 'first body', self.player)
        self.board.post('Second', 'second body', self.other)
        post = dict(self.board.get_post(1))
        editor = {}
        def capture_editor(caller, **kwargs):
            """Capture only the editor transport; run its real save callback."""
            editor.update(kwargs)
        with patch('menus.bboard.EvEditor', capture_editor):
            board_menu.edit_body(staff, '', board=self.board, index=1, post=post)
        self.board.delete_post(1)
        with patch.object(staff, 'msg'):
            self.assertFalse(editor['savefunc'](staff, 'must not replace second'))
        self.assertEqual(self.board.get_post(1)['body'], 'second body')
        self.board.locks.add('post:false();edit:false()')
        with self.assertRaises(BoardError):
            self.board.post('Denied', 'after editor opened', self.player)
        with self.assertRaises(BoardError):
            self.board.edit_post(1, 'denied', actor=staff, expected_id=self.board.get_post(1)['id'])

    def test_channel_session_identity_is_bound_to_current_owner_and_roster(self):
        """Multiple same-account puppets use the sending session, never a foreign session."""
        channel = SimpleNamespace(channel_prefix=lambda: '[QA] ')
        account = self.player.account
        session = SimpleNamespace(account=account, puppet=self.alt)
        output = format_channel_message('hello', channel, senders=[account], sender_session=session)
        self.assertIn(self.alt.key + ': hello', output)
        foreign = SimpleNamespace(account=self.other.account, puppet=self.other)
        output = format_channel_message('hello', channel, senders=[account], sender_session=foreign)
        self.assertIn('(A)', output)
        self.assertNotIn(self.other.key, output)
        self.other.account = None
        unowned = SimpleNamespace(account=account, puppet=self.other)
        self.assertIsNone(active_sender_puppet(account, sender_session=unowned))

    def test_account_summary_uses_only_owned_character_unread_counts(self):
        """Render the real account selector with transport metadata and persisted inboxes."""
        mail.send_character_mail(self.other, self.alt, 'Alt private subject', 'private body')
        mail.send_character_mail(self.player, self.other, 'Foreign account mail', 'foreign body')
        account = self.player.account
        session = SimpleNamespace(sessid=881, protocol_key='QA captured transport', address=('127.0.0.1', 0))
        with patch.object(account.sessions, 'all', return_value=[session]):
            output = account.at_look(target=list(account.characters), session=session)
        self.assertIn(self.alt.key + ' (1)', output)
        self.assertNotIn(self.other.key, output)
        self.assertNotIn('private body', output)
        self.mail(self.alt, 'read', args=str(mail.list_character_mail(self.alt)[0].pk))
        with patch.object(account.sessions, 'all', return_value=[session]):
            output = account.at_look(target=list(account.characters), session=session)
        self.assertNotIn('1 unread mail', output)

    def test_channel_command_routes_real_subscriptions_with_authoritative_session(self):
        """Public subscribers receive the selected character; denied sends route nothing."""
        channel = create_channel(key='qa' + uuid4().hex[:10],
            locks='listen:all();send:all();control:perm(Admin)')
        from django.conf import settings
        self.assertEqual(channel.db_typeclass_path, settings.BASE_CHANNEL_TYPECLASS)
        channel.log_file = None
        # There is no live transport in this suite. Exercise real subscriptions
        # and hooks while capturing delivery to all subscribed test accounts.
        channel.send_to_online_only = False
        self.assertTrue(channel.connect(self.player.account))
        self.assertTrue(channel.connect(self.other.account))
        captured = {account.pk: [] for account in (self.player.account, self.other.account)}
        def receive(account):
            """Capture only Account.msg's final outbound transport payload."""
            def capture(text=None, **kwargs):
                captured[account.pk].append(text[0] if isinstance(text, tuple) else text)
            return capture
        command = CmdChannel()
        command.caller = self.player.account
        command.session = SimpleNamespace(account=self.player.account, puppet=self.alt)
        foreign = SimpleNamespace(account=self.other.account, puppet=self.other)
        with patch.object(self.player.account, 'msg', side_effect=receive(self.player.account)), patch.object(self.other.account, 'msg', side_effect=receive(self.other.account)):
            command.msg_channel(channel, 'ordinary QA channel', sender_session=foreign)
            self.assertIn(self.alt.key, captured[self.other.account.pk][-1])
            self.assertNotIn(self.other.key, captured[self.other.account.pk][-1])
            before = len(captured[self.other.account.pk])
            channel.locks.add('send:perm(Admin)')
            command.msg_channel(channel, 'must not deliver')
            self.assertEqual(len(captured[self.other.account.pk]), before)

    def test_revoked_channel_listen_permission_filters_existing_subscriptions(self):
        """A former public subscriber cannot keep receiving newly restricted traffic."""
        channel = create_channel(key='qa' + uuid4().hex[:10],
            locks='listen:all();send:all();control:perm(Admin)')
        channel.log_file, channel.send_to_online_only = None, False
        staff = fixtures.character(staff=True)
        channel.connect(self.player.account)
        channel.connect(staff.account)
        player_output, staff_output = [], []
        channel.locks.add('listen:perm(Admin);send:perm(Admin)')
        command = CmdChannel()
        command.caller, command.session = staff.account, SimpleNamespace(account=staff.account, puppet=staff)
        def capture(target):
            """Capture final account payloads after the real channel hooks."""
            return lambda text=None, **kwargs: target.append(text)
        with patch.object(self.player.account, 'msg', side_effect=capture(player_output)), patch.object(staff.account, 'msg', side_effect=capture(staff_output)):
            command.msg_channel(channel, 'Staff-only QA traffic')
        self.assertEqual(player_output, [], 'A stale subscription bypassed the new listen lock')
        self.assertEqual(len(staff_output), 1)

    def test_channel_receiver_filter_is_local_to_that_subscriber(self):
        """One subscriber's pre-receive filter cannot suppress another valid receiver."""
        channel = create_channel(key='qa' + uuid4().hex[:10], locks='listen:all();send:all();control:perm(Admin)')
        channel.log_file, channel.send_to_online_only = None, False
        channel.connect(self.player.account)
        channel.connect(self.other.account)
        output = []
        command = CmdChannel()
        command.caller, command.session = self.player.account, SimpleNamespace(account=self.player.account, puppet=self.player)
        with patch.object(self.player.account, 'at_pre_channel_msg', return_value=None), patch.object(self.other.account, 'msg', side_effect=lambda text=None, **kwargs: output.append(text)):
            command.msg_channel(channel, 'valid peer delivery')
        self.assertEqual(len(output), 1)


if __name__ == '__main__':
    with IsolatedPostgres() as database:
        database.create_model_tables()
        from django.apps import apps
        from django.contrib.contenttypes.models import ContentType
        from django.db import connection, connections
        from evennia.comms.models import Msg
        from evennia.typeclasses.attributes import Attribute
        ContentType.objects.get_for_models(*apps.get_models(), for_concrete_models=False)
        with OrdinaryPlayerFixtures('october-communication-qa') as fixtures:
            from evennia.utils.create import create_message, create_script, create_channel
            from commands.player.cmd_mail import CmdMail
            from commands.player.cmd_channel import CmdChannel
            from bboard.commands import CmdBBRead, CmdBBDelete, CmdBBCatchup, CmdBBList, _board_number
            from bboard.bboard import BBoard
            from bboard.transactions import BoardError
            from menus import bboard as board_menu
            from utils import character_mail as mail
            from utils.channel_identity import active_sender_puppet, format_channel_message
            result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CommunicationCases))
            if os.environ.get('PF2_COMMUNICATION_PLAYER_EVIDENCE'):
                Path(os.environ['PF2_COMMUNICATION_PLAYER_EVIDENCE']).write_text(json.dumps(TRANSCRIPT, indent=2), encoding='utf-8')
            raise SystemExit(not result.wasSuccessful())

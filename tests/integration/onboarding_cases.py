"""Ordinary setup callbacks, persistent grants, reconnect, ownership and rollback."""
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

TRANSCRIPT = []


class OnboardingCases(unittest.TestCase):
    """Use actual accounts, User characters, ownership and setup services."""

    def setUp(self):
        """Create two accounts and a same-account alternate in one private room."""
        accounts = [AccountDB.objects.create(username='onboarding-qa-' + uuid4().hex,
            db_typeclass_path='typeclasses.accounts.Account') for _ in range(2)]
        self.room = ObjectDB.objects.create(db_key='Onboarding QA room ' + uuid4().hex[:10],
            db_typeclass_path='typeclasses.rooms.Room')
        self.players = [ObjectDB.objects.create(db_key='Onboarding QA ' + uuid4().hex[:10],
            db_typeclass_path='pokemon.user.User', db_account=account, db_location=self.room) for account in (*accounts, accounts[0])]
        self.player, self.other, self.alt = self.players
        self.messages, self.steps, self.transports = {}, [], []
        for player in self.players:
            player.permissions.add('Player')
            player.tags.add('october-onboarding-qa')
            player.account.characters.add(player)
            Trainer.objects.get_or_create(user=player, defaults={'trainer_number': Trainer.objects.count() + 1})
            UserStorage.objects.get_or_create(user=player)
            self.messages[player.pk] = []
            transport = patch.object(player, 'msg', side_effect=self.messages[player.pk].append)
            transport.start()
            self.transports.append(transport)

    def tearDown(self):
        """Retain labelled menu callback output and verify canonical ownership."""
        for transport in self.transports:
            transport.stop()
        self.assertEqual(list(audit_ownership_v2(apps)), [])
        TRANSCRIPT.append({'case': self._testMethodName, 'steps': self.steps,
            'permissions': [list(player.permissions.all()) for player in self.players],
            'transport': 'captured; menu callbacks replayed; no live socket'})

    def choices(self, kind='human'):
        """Return only native accepted choices used by the ordinary menu."""
        return {'type': kind, 'player_gender': 'Male', 'favored_type': 'Water',
            'species_key': 'Squirtle' if kind == 'human' else 'Eevee', 'species': 'Squirtle' if kind == 'human' else 'Eevee',
            'ability': 'Torrent' if kind == 'human' else 'Run Away', 'nature': 'Hardy', 'starter_gender': 'M'}

    def finish(self, kind='human', player=None):
        """Replay the actual final confirmation node rather than granting directly."""
        actor = player or self.player
        Onboarding(actor).save_draft(self.choices(kind))
        start = len(self.messages[actor.pk])
        getattr(chargen, 'finish_' + kind)(actor, '', expected_choices=self.choices(kind))
        self.steps.append({'character': actor.pk, 'node': 'finish_' + kind, 'output': self.messages[actor.pk][start:]})
        return Onboarding(actor).completion()

    def test_human_finish_receipt_party_stats_and_repeated_confirmation(self):
        """Fresh human completion grants one correctly initialized starter once."""
        row = self.finish()
        self.assertIsNotNone(row, self.messages[self.player.pk])
        pokemon = OwnedPokemon.objects.get(pk=row.pokemon_uuid)
        self.assertEqual((pokemon.level, pokemon.current_hp), (5, get_max_hp(pokemon)))
        self.assertTrue(pokemon.activemoveslot_set.exists())
        self.assertEqual(PokemonPlacement.objects.get(pokemon=pokemon).location_type, 'party')
        chargen.finish_human(self.player, '')
        chargen.finish_fusion(self.player, '')
        self.assertEqual(OwnedPokemon.objects.filter(trainer=self.player.trainer).count(), 1)
        self.assertTrue(self.player.db.chargen_completed)
        self.assertFalse(bool(self.player.db.validated))
        self.assertIn('help getting started', self.messages[self.player.pk][-1])

    def test_initial_fusion_is_canonical_reserved_form_with_full_level_five_xp(self):
        """Initial personal Fusion does not consume a starter or use later unlock XP."""
        row = self.finish('fusion')
        self.assertIsNotNone(row, self.messages[self.player.pk])
        pokemon = OwnedPokemon.objects.get(pk=row.pokemon_uuid)
        self.assertEqual(PokemonPlacement.objects.get(pokemon=pokemon).location_type, 'fusion')
        self.assertEqual(str(self.player.db.fusion_id), str(pokemon.pk))
        self.assertEqual((self.player.db.level, self.player.db.total_exp, self.player.db.fighter_xp), (5, pokemon.total_exp, pokemon.total_exp))
        self.assertEqual(self.player.db.fusion_forms, [str(pokemon.pk)])
        self.assertEqual(len(get_battle_party_with_fusion(self.player)), 1)
        self.assertTrue(pokemon_is_usable(get_battle_party_with_fusion(self.player)[0]))
        self.assertEqual(FusionTransitions(self.player).inspect()['problems'], [])

    def test_saved_choices_resume_after_abort_and_runtime_cache_discard(self):
        """Accepted choices survive a new client without creating any grant."""
        chargen._select_chargen_type(self.player, '', chargen_type='human')
        chargen._select_player_gender(self.player, '', gender='Male', next_node='human_type')
        chargen._select_favored_type(self.player, '', type='Water')
        chargen._handle_starter_species_input(self.player, 'Squirtle')
        chargen.node_abort(self.player)
        self.player.ndb.chargen = None
        self.player.attributes.reset_cache()
        node, kwargs = Onboarding(self.player).resume()
        self.assertEqual(node, 'starter_ability')
        self.assertEqual(self.player.ndb.chargen['species'], 'Squirtle')
        self.assertFalse(OwnedPokemon.objects.filter(trainer=self.player.trainer).exists())
        self.steps.append({'input': 'human / Male / Water / Squirtle / abort / reconnect / chargen', 'resumed_node': node})

    def test_native_choices_are_revalidated_before_any_grant(self):
        """Stale/tampered menu values cannot bypass the final server boundary."""
        for key, value in (('ability', 'Pressure'), ('nature', 'Invented'), ('starter_gender', 'N'),
                ('species_key', 'Arceus'), ('favored_type', 'Invented'), ('type', 'fusion')):
            data = self.choices()
            data[key] = value
            Onboarding(self.player).save_draft(data)
            with self.assertRaises(OnboardingError):
                Onboarding(self.player).complete('human', expected_choices=Onboarding(self.player).draft())
        self.assertFalse(OwnedPokemon.objects.filter(trainer=self.player.trainer).exists())
        self.assertIsNone(Onboarding(self.player).completion())

    def test_concurrent_completion_issues_one_grant_and_identical_receipt(self):
        """Separate database connections serialize the same character's final click."""
        Onboarding(self.player).save_draft(self.choices())
        barrier = Barrier(2)
        def complete():
            """Always close the task-owned worker connection."""
            try:
                barrier.wait(timeout=10)
                return Onboarding(self.player).complete('human', expected_choices=Onboarding(self.player).draft())
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: complete(), range(2)))
        self.assertEqual(results[0], results[1])
        self.assertEqual(OwnedPokemon.objects.filter(trainer=self.player.trainer).count(), 1)

    def test_receipt_failure_rolls_back_starter_and_fusion_attributes_then_retry(self):
        """Real owned/placement/attribute writes roll back with the missing receipt."""
        original = OnboardingCompletion.save
        for actor, kind in ((self.player, 'human'), (self.other, 'fusion')):
            Onboarding(actor).save_draft(self.choices(kind))
            def fail_after_receipt(row, *args, **kwargs):
                """Fail after the actual durable receipt insertion."""
                original(row, *args, **kwargs)
                raise RuntimeError('injected post-completion receipt failure')
            with patch.object(OnboardingCompletion, 'save', fail_after_receipt), self.assertRaises(RuntimeError):
                Onboarding(actor).complete(kind, expected_choices=Onboarding(actor).draft())
            self.assertFalse(OwnedPokemon.objects.filter(trainer=actor.trainer).exists())
            self.assertFalse(bool(actor.db.chargen_completed))
            self.assertFalse(bool(actor.db.fusion_id))
            self.assertEqual(Onboarding(actor).draft()['type'], kind)
            self.assertIsNotNone(Onboarding(actor).complete(kind, expected_choices=Onboarding(actor).draft()))

    def test_same_account_alts_and_separate_account_keep_independent_grants(self):
        """An account membership never substitutes for per-character completion."""
        rows = [self.finish('fusion' if player is self.alt else 'human', player) for player in self.players]
        self.assertEqual({char.pk for char in self.player.account.characters}, {self.player.pk, self.alt.pk})
        self.assertEqual({char.pk for char in self.other.account.characters}, {self.other.pk})
        self.assertEqual(len({row.pokemon_uuid for row in rows}), 3)
        for player, row in zip(self.players, rows):
            self.assertEqual(OwnedPokemon.objects.get(pk=row.pokemon_uuid).trainer_id, player.trainer.pk)
        with self.assertRaises(PlacementError):
            Onboarding(self.player.account)

    def test_legacy_progress_and_active_battle_refuse_extra_grants(self):
        """Existing setup is not guessed away, and battle locks block completion."""
        self.player.db.validated = True
        with self.assertRaises(OnboardingError):
            Onboarding(self.player).save_draft(self.choices())
        Onboarding(self.other).save_draft(self.choices())
        self.other.db.battle_lock = 991
        with self.assertRaises(PlacementError):
            Onboarding(self.other).complete('human', expected_choices=Onboarding(self.other).draft())
        self.assertFalse(OwnedPokemon.objects.filter(trainer__user__in=self.players).exists())

    def test_later_release_preserves_receipt_without_resurrecting_original_grant(self):
        """Completion remains closed after the original starter has left ownership."""
        row = self.finish()
        pokemon = OwnedPokemon.objects.get(pk=row.pokemon_uuid)
        PlacementService(self.player.userstorage).release(pokemon)
        self.assertFalse(OwnedPokemon.objects.filter(pk=row.pokemon_uuid).exists())
        self.assertEqual(Onboarding(self.player).complete('human', expected_choices=Onboarding(self.player).draft()), row.receipt)
        row.refresh_from_db()
        self.assertIsNone(row.pokemon_id)
        self.assertFalse(OwnedPokemon.objects.filter(trainer=self.player.trainer).exists())

    def test_registered_chargen_resumes_and_closes_from_saved_completion(self):
        """Command chooses the persisted next node and never reopens a completed grant."""
        Onboarding(self.player).save_draft({'type': 'human', 'player_gender': 'Male'})
        self.player.ndb.chargen = None
        command = CmdChargen()
        command.caller, command.args = self.player, ''
        with patch('commands.player.cmd_chargen.EnhancedEvMenu') as menu:
            command.func()
            self.assertEqual(menu.call_args.kwargs['startnode'], 'human_type')
            self.assertEqual(menu.call_args.kwargs['startnode_input'], ('', {'gender': 'Male'}))
            self.finish()
            menu.reset_mock()
            command.func()
            menu.assert_not_called()
        self.steps.append({'input': 'chargen / reconnect / chargen / finish / chargen',
            'output': self.messages[self.player.pk][-3:], 'menu_opening': 'constructor captured; callbacks and durable writes real'})

    def test_missing_trainer_number_uses_existing_maximum_and_concurrent_retry(self):
        """Deleted-number gaps cannot make the fallback collide with a live trainer."""
        Trainer.objects.filter(user=self.player).delete()
        Trainer.objects.filter(user=self.other).update(trainer_number=1000)
        trainer = self.player._ensure_trainer()
        self.assertEqual(trainer.trainer_number, 1001)
        self.assertEqual(self.player._ensure_trainer().pk, trainer.pk)

    def test_account_character_creation_initializes_starting_state_and_owner_roster(self):
        """Use Evennia's real create-character path before a normal setup grant."""
        from django.test import override_settings
        account = self.player.account
        account.permissions.add('Player')
        with override_settings(START_LOCATION=f'#{self.room.pk}', DEFAULT_HOME=f'#{self.room.pk}'):
            character, errors = account.create_character(key='Created QA ' + uuid4().hex[:8], description='Tagged onboarding QA')
        self.assertFalse(errors, errors)
        self.assertIsNotNone(character)
        self.assertIn(character, list(account.characters))
        self.assertNotIn(character, list(self.other.account.characters))
        self.assertEqual(character.location.pk, self.room.pk)
        self.assertTrue(Trainer.objects.filter(user=character).exists())
        self.assertTrue(UserStorage.objects.filter(user=character).exists())
        self.assertFalse(OwnedPokemon.objects.filter(trainer__user=character).exists())
        self.assertEqual(set(character.permissions.all()), {'player'})

    def test_real_number_collision_does_not_break_surrounding_creation_transaction(self):
        """A real unique-number error rolls back its savepoint and then retries."""
        from django.db import transaction
        Trainer.objects.filter(user=self.player).delete()
        original = Trainer.objects.get_or_create
        calls = []
        def collision_once(*args, **kwargs):
            """Insert an actually conflicting number before the normal retry."""
            calls.append(True)
            if len(calls) == 1:
                Trainer.objects.create(user=self.player, trainer_number=self.other.trainer.trainer_number)
            return original(*args, **kwargs)
        with transaction.atomic(), patch.object(Trainer.objects, 'get_or_create', collision_once):
            trainer = self.player._ensure_trainer()
            self.player.attributes.add('onboarding_savepoint_qa', 'outer transaction remains usable')
        self.assertEqual(len(calls), 2)
        self.assertEqual(trainer.user_id, self.player.pk)
        self.assertEqual(self.player.db.onboarding_savepoint_qa, 'outer transaction remains usable')

    def test_read_only_staff_inspection_never_completes_or_changes_draft(self):
        """Staff recovery evidence is separate from ordinary completion callbacks."""
        from django.core.management import call_command
        from io import StringIO
        Onboarding(self.player).save_draft(self.choices())
        before = (Onboarding(self.player).draft(), OwnedPokemon.objects.count(), OnboardingCompletion.objects.count())
        output = StringIO()
        call_command('audit_pokemon_onboarding', character=self.player.pk, stdout=output)
        inspected = json.loads(output.getvalue())
        self.assertIsNone(inspected['completion'])
        self.assertEqual(inspected['character'], self.player.pk)
        self.assertEqual((Onboarding(self.player).draft(), OwnedPokemon.objects.count(), OnboardingCompletion.objects.count()), before)


    def test_stale_review_does_not_grant_a_different_saved_choice(self):
        """An old confirmation cannot accept another client's replacement choices."""
        old = self.choices()
        Onboarding(self.player).save_draft(old)
        self.player.ndb.chargen = dict(old)
        _text, options = chargen.starter_confirm(self.player, '')
        yes = next(option for option in options if 'Y' in option.get('key', ()))['goto']
        changed = dict(old, species_key='Bulbasaur', species='Bulbasaur', ability='Overgrow')
        Onboarding(self.player).save_draft(changed)
        node, kwargs = (yes, {}) if isinstance(yes, str) else yes
        getattr(chargen, node)(self.player, 'Y', **kwargs)
        self.assertIsNone(Onboarding(self.player).completion(), 'A stale Squirtle confirmation granted the replacement Bulbasaur')


if __name__ == '__main__':
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from django.apps import apps
        from django.contrib.contenttypes.models import ContentType
        from django.db import connections
        from evennia.accounts.models import AccountDB
        from evennia.objects.models import ObjectDB
        from evennia.commands.command import Command
        from evennia.commands.cmdset import CmdSet
        base_api = patch.multiple(evennia, Command=Command, CmdSet=CmdSet)
        base_api.start()
        from evennia.commands.default.cmdset_account import AccountCmdSet
        from evennia.commands.default.cmdset_character import CharacterCmdSet
        from evennia.commands.default.cmdset_session import SessionCmdSet
        from evennia.commands.default.cmdset_unloggedin import UnloggedinCmdSet
        from evennia.commands.default.muxcommand import MuxCommand
        from evennia.server.sessionhandler import ServerSessionHandler
        from evennia.objects.objects import DefaultObject, DefaultCharacter, DefaultRoom, DefaultExit
        from evennia.scripts.scripts import DefaultScript
        from evennia.utils.search import search_object, search_account
        from evennia.commands import cmdhandler
        # Bind real standalone facilities without constructing an Evennia service
        # or opening ports. Registration/socket journeys remain separate.
        api = patch.multiple(evennia, Command=Command, CmdSet=CmdSet,
            DefaultObject=DefaultObject, DefaultCharacter=DefaultCharacter,
            DefaultRoom=DefaultRoom, DefaultExit=DefaultExit, DefaultScript=DefaultScript,
            SESSION_HANDLER=ServerSessionHandler(), search_object=search_object, search_account=search_account,
            default_cmds=SimpleNamespace(CharacterCmdSet=CharacterCmdSet, AccountCmdSet=AccountCmdSet,
                SessionCmdSet=SessionCmdSet, UnloggedinCmdSet=UnloggedinCmdSet, MuxCommand=MuxCommand),
            syscmdkeys=SimpleNamespace(**{key: getattr(cmdhandler, key) for key in
                ('CMD_NOINPUT', 'CMD_NOMATCH', 'CMD_MULTIMATCH', 'CMD_LOGINSTART')}))
        api.start()
        ContentType.objects.get_for_models(*apps.get_models(), for_concrete_models=False)
        with patch.object(evennia, 'Command', Command), patch.object(evennia, 'CmdSet', CmdSet):
            from menus import chargen
            from commands.player.cmd_chargen import CmdChargen
        from pokemon.helpers.party_helpers import pokemon_is_usable
        from pokemon.helpers.pokemon_helpers import get_max_hp
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.onboarding import OnboardingCompletion
        from pokemon.models.storage import PokemonPlacement, UserStorage
        from pokemon.models.trainer import Trainer
        from pokemon.services.fusion_transitions import FusionTransitions
        from pokemon.services.onboarding import Onboarding, OnboardingError
        from pokemon.services.ownership_audit import audit_ownership_v2
        from pokemon.services.placement import PlacementError, PlacementService
        from utils.fusion import get_battle_party_with_fusion
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(OnboardingCases))
        if os.environ.get('PF2_ONBOARDING_PLAYER_EVIDENCE'):
            Path(os.environ['PF2_ONBOARDING_PLAYER_EVIDENCE']).write_text(json.dumps(TRANSCRIPT, indent=2), encoding='utf-8')
        raise SystemExit(not result.wasSuccessful())

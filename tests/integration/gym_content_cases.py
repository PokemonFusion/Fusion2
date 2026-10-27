"""Versioned gym authoring and ordinary player launch on real PostgreSQL records."""

import copy
from io import StringIO
import json
import os
from pathlib import Path
import random
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres

TRANSCRIPT = []


class GymContentCases(unittest.TestCase):
    """Separate reusable-author acceptance from the existing first Tempo gym suite."""

    def setUp(self):
        """Create tagged ordinary users, a private room and one validation definition."""
        suffix = uuid4().hex[:12]
        account = AccountDB.objects.create(username='gym-content-qa-' + suffix)
        self.player = ObjectDB.objects.create(db_key='Gym Content QA ' + suffix,
            db_typeclass_path='pokemon.user.User', db_account=account)
        self.player.permissions.add('Player')
        self.player.tags.add('october-gym-content-qa')
        self.room = ObjectDB.objects.create(db_key='Gym content room ' + suffix,
            db_typeclass_path='typeclasses.rooms.Room')
        self.player.location = self.room
        trainer, _ = Trainer.objects.get_or_create(user=self.player,
            defaults={'trainer_number': Trainer.objects.count() + 1})
        UserStorage.objects.get_or_create(user=self.player)
        self.owned = create_owned_pokemon('Jolteon', trainer, 50, nature='Hardy', ivs=[0]*6, evs=[0]*6,
            active_move_names=['Tackle', 'Thunderbolt'])
        self.messages, self.steps, self.session = [], [], None
        self.transport = patch.object(self.player, 'msg', side_effect=self.messages.append)
        self.transport.start()
        # PF2_NO_EVENNIA deliberately disables the global search facade. Bind
        # its dbref lookup to the real ORM rather than fabricating a controller.
        self.search = patch('pokemon.battle.battleinstance.search_object',
            side_effect=lambda query: list(ObjectDB.objects.filter(pk=int(str(query).lstrip('#')))))
        self.search.start()
        self.definition = json.loads((ROOT / 'world/content/gyms/validation_singles.json').read_text(encoding='utf-8'))
        self.definition['gym_key'] = 'validation_' + suffix
        self.definition['leader']['name'] += ' ' + suffix
        self.definition['badge']['name'] += ' ' + suffix
        self.definition['profile']['badge_key'] = 'validation_badge_' + suffix

    def tearDown(self):
        """Release only the case battle and retain actual ordinary command output."""
        if self.session and not getattr(self.session, '_ended', False):
            self.session.end()
        self.transport.stop()
        self.search.stop()
        TRANSCRIPT.append({'case': self._testMethodName, 'commands': self.steps,
            'permissions': list(self.player.permissions.all()), 'transport': 'captured; no live socket'})

    def command(self, arguments):
        """Run the actual registered gym command with its ordinary caller."""
        start = len(self.messages)
        command = CmdGym()
        command.caller, command.args = self.player, arguments
        command.func()
        self.steps.append({'input': '+gym ' + arguments, 'output': self.messages[start:]})
        return self.messages[-1]

    def install(self, *, eligible=True):
        """Install via the shared service; badge grants here are labelled fixture setup."""
        profile = install_gym_content(self.definition)
        if eligible:
            self.player.trainer.add_badge(seed_production_gym_content().profile.badge)
        return profile

    def launch(self):
        """Enter through ordinary +gym and retain the resulting real session."""
        self.command('challenge ' + self.definition['gym_key'])
        self.session = self.player.ndb.battle_instance
        self.assertIsNotNone(self.session, self.messages)
        self.session.battle.rng = random.Random(9)

    def rebuild(self):
        """Restore the actual persisted room checkpoint after discarding runtime caches."""
        self.session._sync_active_battle_state()
        self.session._persist_turn_state()
        battle_id = self.session.battle_id
        battle_handler.unregister(self.session)
        self.player.ndb.battle_instance = None
        self.room.ndb.battle_instances = {}
        self.session = BattleSession.restore(self.room, battle_id)
        self.assertIsNotNone(self.session)

    def win(self):
        """Use legal ordinary move declarations until the authored team is defeated."""
        for _ in range(12):
            self.session.queue_move('Thunderbolt', 'B1', caller=self.player, actor='A1')
            if getattr(self.session, '_ended', False) or self.session.battle.battle_over:
                return
        self.fail(f'Validation singles did not finish in twelve turns: {self.messages[-18:]} {self.session.turn_state}')

    def test_same_author_service_loads_tempo_and_distinct_singles(self):
        """Format, eligibility, AI, rules and cooldown vary entirely through content."""
        tempo = seed_production_gym_content().profile
        single = self.install(eligible=False)
        self.assertEqual((tempo.battle_format, single.battle_format), ('double', 'single'))
        before = EncounterPokemon.objects.count()
        self.assertIn('Requires at least 1', self.command('challenge ' + single.gym_key))
        self.assertEqual(EncounterPokemon.objects.count(), before)
        self.player.trainer.add_badge(tempo.badge)
        output = self.command('check ' + single.gym_key)
        self.assertIn('Singles', output)
        self.assertIn('one level 5 Eevee', output)
        self.launch()
        self.assertEqual(self.session.encounter_metadata['content_version'], 1)
        self.assertEqual(self.session.battle.participants[1].ai_profile, 'gym_leader')
        self.assertEqual(len(self.session.choices_for(self.player).positions()), 1)

    def test_updated_content_does_not_change_running_or_pending_victory(self):
        """Reload preserves launch definition and an old victory remains claimable once."""
        profile = self.install()
        self.launch()
        captured = copy.deepcopy(dict(self.session.encounter_metadata))
        changed = copy.deepcopy(self.definition)
        changed['version'] = 2
        changed['profile']['rematch_cooldown_seconds'] = 120
        changed['profile']['rules_text'] += ' Updated author version.'
        changed['team'][0]['level'] = 6
        updated = install_gym_content(changed)
        self.assertEqual(updated.badge_id, profile.badge_id)
        self.rebuild()
        self.assertEqual(self.session.encounter_metadata['content_digest'], captured['content_digest'])
        self.assertEqual(self.session.encounter_metadata['content_definition']['team'][0]['level'], 5)
        original = Trainer.add_badge
        def fail_after_write(trainer, badge):
            """Exercise an actual badge insertion followed by a recoverable delivery fault."""
            original(trainer, badge)
            raise RuntimeError('injected pending gym delivery')
        with patch.object(Trainer, 'add_badge', fail_after_write):
            self.win()
        victory = GymVictory.objects.get(player=self.player, metadata__badge_id=profile.badge_id)
        self.assertIsNone(victory.claimed_at)
        self.assertEqual(victory.metadata['content_version'], 1)
        self.assertIn('First clear complete', self.command('claim'))
        self.assertIn('No unclaimed', self.command('claim'))
        self.assertEqual(self.player.trainer.badges.filter(pk=profile.badge_id).count(), 1)

    def test_first_clear_practice_rematch_and_no_repeat_progression(self):
        """Zero configured cooldown permits immediate practice with one total badge."""
        profile = self.install()
        before = (self.player.trainer.money, self.owned.level, self.owned.total_exp, list(self.owned.evs))
        for kind in ('first_clear', 'rematch'):
            self.launch()
            self.win()
            victory = GymVictory.objects.filter(player=self.player, metadata__badge_id=profile.badge_id).latest('recorded_at')
            self.assertEqual(victory.award_kind, kind)
            self.assertIsNotNone(victory.claimed_at)
        self.owned.refresh_from_db()
        self.player.trainer.refresh_from_db()
        self.assertEqual((self.player.trainer.money, self.owned.level, self.owned.total_exp, self.owned.evs), before)
        self.assertEqual(self.player.trainer.badges.filter(pk=profile.badge_id).count(), 1)

    def test_idempotent_install_upgrade_conflicts_and_concurrent_install(self):
        """Stable identities and exact repeat installs preserve team and reward rows."""
        profile = self.install()
        identities = (profile.pk, profile.badge_id, profile.npc_trainer_id, list(profile.npc_trainer.pokemon_templates.values_list('pk', flat=True)))
        barrier = Barrier(2)
        def install():
            """Compete on separate PostgreSQL connections, always closing them."""
            try:
                barrier.wait(timeout=10)
                return install_gym_content(self.definition).pk
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(lambda _: install(), range(2))), [profile.pk]*2)
        again = install_gym_content(self.definition)
        self.assertEqual(identities, (again.pk, again.badge_id, again.npc_trainer_id, list(again.npc_trainer.pokemon_templates.values_list('pk', flat=True))))
        changed = copy.deepcopy(self.definition)
        changed['team'][0]['level'] = 6
        with self.assertRaisesRegex(ValueError, 'higher version'):
            install_gym_content(changed)
        changed['version'] = 2
        install_gym_content(changed)
        with self.assertRaisesRegex(ValueError, 'downgrades'):
            install_gym_content(self.definition)

    def test_invalid_content_refuses_before_writes_or_battle_allocation(self):
        """Strict author validation refuses unsupported policy, teams and ignored keys."""
        changes = [('profile', 'battle_format', 'multi'), ('profile', 'strategy_key', 'weather'),
            ('profile', 'ai_profile', 'invented'), ('profile', 'reward_policy', 'money'),
            ('profile', 'required_badge_count', -1), ('profile', 'rematch_cooldown_seconds', True),
            ('profile', 'item_clause', 'invented')]
        before = (NPCTrainer.objects.count(), GymLeaderProfile.objects.count(), EncounterPokemon.objects.count())
        for section, key, value in changes:
            invalid = copy.deepcopy(self.definition)
            invalid[section][key] = value
            with self.assertRaises(ValueError):
                install_gym_content(invalid)
        for key, value in (('level', 101), ('ability', 'Pressure'), ('move_names', ['Invented Move']), ('ivs', [32]*6), ('evs', [252]*6)):
            invalid = copy.deepcopy(self.definition)
            invalid['team'][0][key] = value
            with self.assertRaises(ValueError):
                install_gym_content(invalid)
        self.assertEqual((NPCTrainer.objects.count(), GymLeaderProfile.objects.count(), EncounterPokemon.objects.count()), before)

    def test_direct_rule_or_team_drift_fails_before_allocation_and_reinstall_repairs_owned_rows(self):
        """A raw staff edit cannot silently become the installed battle version."""
        profile = self.install()
        before = EncounterPokemon.objects.count()
        GymLeaderProfile.objects.filter(pk=profile.pk).update(rematch_cooldown_seconds=99)
        self.assertIn('installed version', self.command('challenge ' + profile.gym_key))
        self.assertEqual(EncounterPokemon.objects.count(), before)
        install_gym_content(self.definition)
        profile.npc_trainer.pokemon_templates.update(level=6)
        self.assertIn('installed version', self.command('challenge ' + profile.gym_key))
        self.assertEqual(EncounterPokemon.objects.count(), before)
        install_gym_content(self.definition)
        self.launch()

    def test_badge_or_leader_identity_cannot_be_reassigned_by_content_upgrade(self):
        """Author updates cannot turn a rematch into a new first-clear reward."""
        profile = self.install()
        for section, key in (('badge', 'name'), ('badge', 'region'), ('leader', 'name'), ('profile', 'badge_key')):
            changed = copy.deepcopy(self.definition)
            changed['version'] = 2
            changed[section][key] += '_new'
            with self.assertRaisesRegex(ValueError, 'identities are stable'):
                install_gym_content(changed)
        profile.refresh_from_db()
        self.assertEqual(profile.content_version, 1)

    def test_installer_failure_rolls_back_real_roster_updates(self):
        """A fault after a real template save leaves no half-updated content version."""
        profile = self.install()
        changed = copy.deepcopy(self.definition)
        changed['version'] = 2
        changed['team'][0]['level'] = 6
        original = NPCPokemonTemplate.save
        def fail_after_save(row, *args, **kwargs):
            """Retain the actual write before injecting its rollback proof."""
            original(row, *args, **kwargs)
            raise RuntimeError('injected content roster update failure')
        with patch.object(NPCPokemonTemplate, 'save', fail_after_save), self.assertRaises(RuntimeError):
            install_gym_content(changed)
        profile.refresh_from_db()
        self.assertEqual(profile.content_version, 1)
        self.assertEqual(profile.npc_trainer.pokemon_templates.get().level, 5)
        self.assertEqual(GymContent.from_profile(profile).digest, profile.content_digest)

    def test_singles_concession_has_no_reward_or_cooldown(self):
        """The same configured no-loss-penalty rule applies to the second format."""
        profile = self.install()
        self.launch()
        command = CmdBattleConcede()
        command.caller, command.args = self.player, 'yes'
        with patch('commands.player.cmd_battle_concede.get_system', return_value=SimpleNamespace(battle_manager=None)):
            command.func()
        self.assertFalse(GymVictory.objects.filter(player=self.player, metadata__badge_id=profile.badge_id).exists())
        self.assertFalse(self.player.trainer.badges.filter(pk=profile.badge_id).exists())
        self.launch()

    def test_author_command_validation_is_read_only_and_repeat_install_is_idempotent(self):
        """The shipped author path validates files and reports actionable invalid rules."""
        from django.core.management import call_command
        from django.core.management.base import CommandError
        from tempfile import TemporaryDirectory
        with TemporaryDirectory(prefix='pf2-gym-content-') as temporary:
            path = Path(temporary) / 'gym.json'
            path.write_text(json.dumps(self.definition), encoding='utf-8')
            before = GymLeaderProfile.objects.count()
            output = StringIO()
            call_command('install_gym_content', str(path), check=True, stdout=output)
            self.assertIn('Valid ', output.getvalue())
            self.assertEqual(GymLeaderProfile.objects.count(), before)
            for _ in range(2):
                call_command('install_gym_content', str(path), stdout=StringIO())
            self.assertEqual(GymLeaderProfile.objects.count(), before + 1)
            invalid = copy.deepcopy(self.definition)
            invalid['profile']['battle_format'] = ['single']
            path.write_text(json.dumps(invalid), encoding='utf-8')
            with self.assertRaisesRegex(CommandError, 'battle_format'):
                call_command('install_gym_content', str(path), check=True, stdout=StringIO())


if __name__ == '__main__':
    ROOT = Path(__file__).resolve().parents[2]
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
        ContentType.objects.get_for_models(*apps.get_models(), for_concrete_models=False)
        with patch.object(evennia, 'Command', Command), patch.object(evennia, 'CmdSet', CmdSet):
            from commands.player.cmd_gym import CmdGym
            from commands.player.cmd_battle_concede import CmdBattleConcede
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle.handler import battle_handler
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.models.core import EncounterPokemon
        from pokemon.models.gym import GymVictory
        from pokemon.models.storage import UserStorage
        from pokemon.models.trainer import GymLeaderProfile, NPCPokemonTemplate, NPCTrainer, Trainer
        from pokemon.services.gym_content import GymContent, install_gym_content
        from pokemon.services.production_gym_seed import seed_production_gym_content
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(GymContentCases))
        if os.environ.get('PF2_GYM_CONTENT_PLAYER_EVIDENCE'):
            Path(os.environ['PF2_GYM_CONTENT_PLAYER_EVIDENCE']).write_text(json.dumps(TRANSCRIPT, indent=2), encoding='utf-8')
        raise SystemExit(not result.wasSuccessful())

"""Actual character/profile requests and read-only canonical sheet projections."""

import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
from ordinary_player_fixtures import OrdinaryPlayerFixtures

TRANSCRIPT = []


class SheetCases(unittest.TestCase):
    """Use two same-account characters, an outsider and actual saved resources."""

    def setUp(self):
        """Create disposable ordinary players; capture only command transport."""
        self.player = fixtures.character()
        self.alt = fixtures.character(account=self.player.account)
        self.other = fixtures.character()
        self.mon = create_owned_pokemon('Squirtle', self.player.trainer, 20, nature='Hardy',
            ivs=[1, 2, 3, 4, 5, 6], evs=[0] * 6, active_move_names=['Tackle', 'Water Gun'])
        PlacementService(existing_storage(self.player)).to_party(self.mon, 3)
        self.steps = []

    def tearDown(self):
        """Record normal permissions and the exact request/command boundary."""
        TRANSCRIPT.append({'case': self._testMethodName, 'steps': self.steps,
            'permissions': [list(char.permissions.all()) for char in (self.player, self.alt, self.other)],
            'transport': 'Django request rendering and captured command output; no live browser/socket'})

    def hub(self, account=None):
        """Render the actual authenticated view and template with real request user."""
        request = RequestFactory().get('/mysheet/')
        request.user = account or self.player.account
        request.session = {}
        response = MySheetView.as_view()(request)
        response.render()
        self.steps.append({'request': '/mysheet/', 'account': request.user.pk, 'status': response.status_code})
        return response, response.content.decode()

    def sheet(self, actor=None, args='', switches=()):
        """Execute the normal sheet command without replacing resource reads."""
        actor = actor or self.player
        output = []
        command = CmdSheet()
        command.caller, command.args, command.switches = actor, args, list(switches)
        command.parse()
        with patch.object(actor, 'msg', side_effect=output.append):
            command.func()
        text = '\n'.join(str(value) for value in output)
        self.steps.append({'command': '+sheet' + ('/' + '/'.join(switches) if switches else '') + ' ' + args,
                           'character': actor.pk, 'output': text})
        return text

    def test_private_fields_survive_saver_reload_and_user_lookup(self):
        """Actual persisted Saver mappings retain private flags through +profile."""
        set_profile_field(self.player, 'Secret', 'PRIVATE_SENTINEL', private=True)
        set_profile_field(self.player, 'Public', 'PUBLIC_SENTINEL', private=False)
        self.player.attributes.reset_cache()
        self.assertTrue(get_profile_fields(self.player)['secret']['private'])
        self.assertNotIn('secret', visible_profile_fields(self.player, self.other))
        self.assertIn('secret', visible_profile_fields(self.player, self.player.account))
        output = []
        command = CmdProfile()
        command.caller, command.args, command.switches = self.other, self.player.key, []
        with patch.object(self.other, 'msg', side_effect=output.append):
            command.func()
        text = str(output)
        self.assertIn('PUBLIC_SENTINEL', text)
        self.assertNotIn('PRIVATE_SENTINEL', text)
        self.steps.append({'command': '+profile ' + self.player.key, 'output': text})

    def test_account_character_integer_collision_does_not_grant_private_access(self):
        """AccountDB and ObjectDB IDs are distinct identity domains."""
        owner = ObjectDB.objects.create(pk=30000, db_key='Collision owner', db_typeclass_path='pokemon.user.User')
        foreign = AccountDB.objects.create(pk=30000, username='collision-' + uuid4().hex,
            db_typeclass_path='typeclasses.accounts.Account')
        set_profile_field(owner, 'Secret', 'NEVER_PUBLIC', private=True)
        self.assertFalse(can_view_private_fields(foreign, owner))
        self.assertEqual(visible_profile_fields(owner, foreign), {})

    def test_fresh_roster_rejects_foreign_hub_and_stale_removed_ownership(self):
        """Caller-supplied subsets cannot widen account authority or reuse old caches."""
        self.assertEqual(build_player_hub_entries(self.player.account, [self.other]), [])
        self.assertEqual(select_profile_character(self.player.account, self.alt.pk), self.alt)
        self.assertIsNone(select_profile_character(self.player.account, self.other.pk))
        list(self.player.account.characters.all())
        # Staff prerequisite: emulate an independent saved roster update.
        self.player.account.attributes.add('_playable_characters', [self.player])
        self.assertIsNone(select_profile_character(self.player.account, self.alt.pk))
        self.assertEqual([row['character_id'] for row in build_player_hub_entries(self.player.account)], [self.player.pk])

    def test_anonymous_routes_redirect_and_foreign_profile_post_cannot_edit(self):
        """Request dispatch enforces login and refuses an explicit unowned selector."""
        anonymous = RequestFactory().get('/mysheet/')
        anonymous.user = AnonymousUser()
        self.assertEqual(MySheetView.as_view()(anonymous).status_code, 302)
        self.assertEqual(ProfileEditorView.as_view()(anonymous).status_code, 302)
        request = RequestFactory().post('/profiles/', {'character': self.other.pk, 'field_name': 'Secret', 'field_text': 'FORGED'})
        request.user = self.player.account
        with patch('web.website.views.profile_editor.messages.error'):
            response = ProfileEditorView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(get_profile_fields(self.other), {})
        self.assertEqual(get_profile_fields(self.player), {})

    def test_owned_alt_profile_post_is_scoped_and_escaped(self):
        """The owner can edit the selected alternate without touching the first."""
        request = RequestFactory().post('/profiles/', {'character': self.alt.pk, 'field_name': 'Appearance',
            'field_text': '<script>NEVER_EXECUTE</script>', 'private': '1'})
        request.user = self.player.account
        with patch('web.website.views.profile_editor.messages.success'):
            self.assertEqual(ProfileEditorView.as_view()(request).status_code, 302)
        self.assertEqual(get_profile_fields(self.player), {})
        self.assertTrue(get_profile_fields(self.alt)['appearance']['private'])
        get = RequestFactory().get('/profiles/', {'character': self.alt.pk})
        get.user = self.player.account
        get.session = {}
        text = ProfileEditorView.as_view()(get).render().content.decode()
        self.assertIn('&lt;script&gt;', text)
        self.assertNotIn('<script>NEVER_EXECUTE', text)

    def test_partial_character_views_do_not_create_any_setup_rows(self):
        """Actual User properties must not create trainer/storage/boxes during reads."""
        partial = ObjectDB.objects.create(db_key='Partial QA ' + uuid4().hex[:8], db_typeclass_path='pokemon.user.User',
            db_account=self.player.account)
        partial.permissions.add('Player')
        self.player.account.characters.add(partial)
        # Separate staff prerequisite: model an interrupted/legacy setup after
        # normal typeclass construction has initialized its empty records.
        Trainer.objects.filter(user=partial).delete()
        UserStorage.objects.filter(user=partial).delete()
        before = (Trainer.objects.count(), UserStorage.objects.count(), StorageBox.objects.count(), OwnedPokemon.objects.count())
        _, text = self.hub()
        self.assertIn('setup is incomplete', text)
        self.sheet(partial)
        self.sheet(partial, switches=['inv'])
        command = CmdSheetPokemon()
        command.caller, command.args, command.switches = partial, '', []
        command.parse()
        with patch.object(partial, 'msg'):
            command.func()
        self.assertEqual(before, (Trainer.objects.count(), UserStorage.objects.count(), StorageBox.objects.count(), OwnedPokemon.objects.count()))

    def test_gapped_slots_wallet_inventory_badges_and_saved_condition_are_fresh(self):
        """The web and game agree after item/reward writers update saved rows."""
        trainer = self.player.trainer
        trainer.add_item('Potion', 2)
        trainer.badges.add(GymBadge.objects.create(name='QA Badge', region='QA'))
        Trainer.objects.filter(pk=trainer.pk).update(money=4321)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=2, status='psn', held_item='Oran Berry', is_shiny=True)
        ActiveMoveslot.objects.filter(pokemon=self.mon).update(current_pp=2)
        response, web = self.hub()
        entry = next(row for row in response.context_data['characters'] if row['character_id'] == self.player.pk)
        self.assertEqual([slot for slot, _ in entry['party_slots']], [3])
        self.assertEqual(entry['trainer'].money, 4321)
        self.assertIn('>3</span>', web)
        for value in ('4321', 'Potion', 'QA Badge', 'Oran Berry', 'psn', 'Shiny'):
            self.assertIn(value, web)
        game = self.sheet(args='3')
        for value in ('Oran Berry', '2/', 'psn'):
            self.assertIn(value, game)
        self.assertIn('4,321', self.sheet())
        self.assertIn('empty', self.sheet(args='1'))

    def test_daycare_custody_and_retrieval_never_become_box_fallback(self):
        """Ordinary Daycare service transitions display the right custody group."""
        Trainer.objects.filter(user=self.player).update(money=1000)
        entry = Daycare(self.player).deposit('3')
        snapshot = canonical_roster(self.player)
        self.assertEqual((snapshot['party'], snapshot['boxed']), ([], []))
        self.assertEqual(snapshot['reserved'][0]['activity'], 'daycare')
        self.assertIn('Daycare reservation', self.hub()[1])
        Daycare(self.player).retrieve(entry.pk)
        self.assertEqual(canonical_roster(self.player)['reserved'], [])
        self.assertEqual(len(canonical_roster(self.player)['party']), 1)

    def test_trade_reservation_and_completion_move_visible_owner(self):
        """Consent trade is shown reserved until settlement, then only at new owner."""
        offer = TradeOffers(self.player).propose(self.other.key, '3')
        self.assertIn('Reserved: trade', self.hub()[1])
        TradeOffers(self.other).inspect(offer.pk)
        TradeOffers(self.other).accept(offer.pk)
        self.assertEqual(canonical_roster(self.player)['pokemon'], [])
        self.assertEqual(canonical_roster(self.other)['pokemon'][0].pk, self.mon.pk)
        self.assertNotIn('Squirtle', self.hub()[1])
        self.assertIn('Squirtle', self.hub(self.other.account)[1])

    def test_missing_placement_is_visible_and_no_read_repair_occurs(self):
        """Malformed state remains explicit instead of guessed boxed/party state."""
        PokemonPlacement.objects.filter(pokemon=self.mon).delete()
        snapshot = canonical_roster(self.player)
        self.assertEqual((snapshot['party'], snapshot['boxed']), ([], []))
        self.assertEqual(len(snapshot['unplaced']), 1)
        self.assertIn('missing or conflicting placement', self.hub()[1])
        self.assertIn('staff inspection', self.sheet(args='3'))
        self.assertFalse(PokemonPlacement.objects.filter(pokemon=self.mon).exists())

    def test_fusion_reservation_and_model_sheet_keep_effective_battle_values(self):
        """An active owner-derived form is not an extra boxed party member."""
        PlacementService(existing_storage(self.player)).reserve_for_fusion(self.mon)
        self.player.db.fusion_id = str(self.mon.pk)
        self.player.db.fusion_kind = 'permanent'
        self.player.db.fighter_xp = self.mon.total_exp
        snapshot = canonical_roster(self.player)
        self.assertEqual(snapshot['boxed'], [])
        self.assertEqual(snapshot['reserved'][0]['location'], 'Fusion reservation')
        self.assertIn('Fusion reservation', self.hub()[1])
        self.assertIn('Squirtle', self.sheet())

    def test_fresh_owned_read_discards_old_active_form_annotations(self):
        """Deactivated form adapters cannot contaminate later normal model reads."""
        from pokemon.services.ownership import fresh_owned
        self.mon._pf2_active_fusion = True
        self.mon._pf2_fusion_level = 4
        self.mon._pf2_fusion_xp = 1
        row = canonical_roster(self.player)['party'][0]
        self.assertFalse(hasattr(row, '_pf2_active_fusion'))
        self.assertFalse(hasattr(row, '_pf2_fusion_level'))
        self.assertEqual(row.level, 20)

    def test_conflicting_legacy_membership_remains_visible_without_repair(self):
        """Read projection must not conceal or erase a damaged mirror."""
        existing_storage(self.other).stored_pokemon.add(self.mon)
        snapshot = canonical_roster(self.player)
        self.assertEqual(snapshot['party'], [])
        self.assertIn('conflicting storage membership', self.hub()[1])
        self.assertTrue(existing_storage(self.other).stored_pokemon.filter(pk=self.mon.pk).exists())

    def test_normal_field_use_updates_both_inventory_and_saved_pokemon_display(self):
        """A real +use transaction is visible immediately and after cache discard."""
        from commands.player.cmd_inventory import CmdUseItem
        from pokemon.helpers.pokemon_helpers import get_max_hp
        trainer = self.player.trainer
        trainer.add_item('Potion', 2)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=1)
        self.hub()
        self.sheet(args='3')
        output = []
        command = CmdUseItem()
        command.caller, command.args = self.player, 'Potion=3'
        command.parse()
        with patch.object(self.player, 'msg', side_effect=output.append):
            command.func()
        self.assertIn('Used Potion', str(output))
        self.player.attributes.reset_cache()
        snapshot = canonical_roster(self.player)
        self.assertEqual(snapshot['party'][0].current_hp, min(21, get_max_hp(snapshot['party'][0])))
        self.assertEqual(snapshot['trainer'].get_item_quantity('Potion'), 1)
        response, _ = self.hub()
        own = next(row for row in response.context_data['characters'] if row['character_id'] == self.player.pk)
        self.assertEqual(own['inventory'][0].quantity, 1)
        self.assertIn('21', self.sheet(args='3'))
        self.steps.append({'command': '+use Potion=3', 'output': output})


if __name__ == '__main__':
    with IsolatedPostgres() as database:
        database.create_model_tables()
        from django.apps import apps
        from django.contrib.contenttypes.models import ContentType
        ContentType.objects.get_for_models(*apps.get_models(), for_concrete_models=False)
        with OrdinaryPlayerFixtures('october-sheet-qa') as fixtures:
            from django.contrib.auth.models import AnonymousUser
            from django.test import RequestFactory
            from evennia.accounts.models import AccountDB
            from evennia.objects.models import ObjectDB
            from pokemon.helpers.pokemon_helpers import create_owned_pokemon
            from pokemon.models.core import OwnedPokemon
            from pokemon.models.moves import ActiveMoveslot
            from pokemon.models.storage import PokemonPlacement, StorageBox, UserStorage
            from pokemon.models.trainer import Trainer, GymBadge
            from pokemon.services.placement import PlacementService
            from pokemon.services.daycare import Daycare
            from pokemon.services.trading import TradeOffers
            from utils.character_profiles import set_profile_field, get_profile_fields, visible_profile_fields, can_view_private_fields
            from utils.character_reads import canonical_roster, existing_storage
            from commands.player.cmd_profile import CmdProfile
            from commands.player.cmd_sheet import CmdSheet, CmdSheetPokemon
            from web.website.views.mysheet import MySheetView, build_player_hub_entries
            from web.website.views.profile_editor import ProfileEditorView, select_profile_character
            result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SheetCases))
            if os.environ.get('PF2_SHEET_PLAYER_EVIDENCE'):
                Path(os.environ['PF2_SHEET_PLAYER_EVIDENCE']).write_text(json.dumps(TRANSCRIPT, indent=2), encoding='utf-8')
            raise SystemExit(not result.wasSuccessful())

"""Four ordinary controller commands, durable lobbies and exact session recovery."""

import json
import os
import random
import re
from copy import deepcopy
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
from ordinary_player_fixtures import OrdinaryPlayerFixtures

TRANSCRIPT = []


class MultiBattleCases(unittest.TestCase):
    """Use actual four-account Player characters; capture only session transport."""

    def setUp(self):
        """Create four tagged controllers and their independent gapped own parties."""
        self.room = ObjectDB.objects.create(db_key='Multi QA ' + uuid4().hex[:8], db_typeclass_path='typeclasses.rooms.Room')
        self.players, self.transports, self.outputs, self.steps = {}, [], {}, []
        for label in ('A1', 'A2', 'B1', 'B2'):
            player = fixtures.character()
            player.location = self.room
            self.players[label] = player
            self.outputs[player.pk] = []
            for capture in (patch.object(player, 'msg', side_effect=lambda text=None, _id=player.pk, **kwargs: self.outputs[_id].append(text)),
                            patch.object(player.sessions, 'all', return_value=[SimpleNamespace(protocol_key='captured-QA')])):
                capture.start()
                self.transports.append(capture)
            for species, slot in (('Squirtle', 3), ('Eevee', 6)):
                mon = create_owned_pokemon(species, player.trainer, 20, nature='Hardy', ability='Torrent' if species == 'Squirtle' else 'Run Away',
                    ivs=[0] * 6, evs=[0] * 6, active_move_names=['Tackle', 'Water Gun', 'Surf', 'Helping Hand'])
                PlacementService(existing_storage(player)).to_party(mon, slot)
        self.session = None

    def tearDown(self):
        """Release only tagged case state; the enclosing schema is always dropped."""
        if self.session and self.session.logic:
            self.session.end()
        for capture in reversed(self.transports):
            capture.stop()
        TRANSCRIPT.append({'case': self._testMethodName, 'steps': self.steps,
            'permissions': [list(player.permissions.all()) for player in self.players.values()],
            'transport': 'captured Player.msg and online-session fixture; no live sockets'})
        if os.environ.get('PF2_MULTI_PLAYER_EVIDENCE'):
            Path(os.environ['PF2_MULTI_PLAYER_EVIDENCE']).write_text(json.dumps(TRANSCRIPT, indent=2), encoding='utf-8')

    def lobby(self, label, args):
        """Execute the actual registered ordinary Multi command."""
        player = self.players[label]
        before = len(self.outputs[player.pk])
        command = CmdPvpMulti()
        command.caller, command.args = player, args
        command.func()
        output = self.outputs[player.pk][before:]
        self.steps.append({'character': player.pk, 'input': '+pvp/multi ' + args, 'output': output})
        return str(output)

    def launch(self):
        """Create/join/ready/start through four independently authorized commands."""
        self.lobby('A1', 'create')
        for label in ('A2', 'B1', 'B2'):
            self.lobby(label, 'join ' + label)
        for label in self.players:
            self.lobby(label, 'ready')
        self.lobby('A1', 'start')
        self.session = self.players['A1'].ndb.battle_instance
        self.assertIsNotNone(self.session, self.outputs)
        self.assertEqual(len(self.session.battle.participants), 4)
        return self.session

    def command(self, label, kind, args):
        """Run normal attack/switch/item/concede commands against the real session."""
        from commands.player import cmd_battle_attack, cmd_battle_switch, cmd_battle_item, cmd_battle_concede
        from commands.player import cmd_battle_tera, cmd_battle_mega, cmd_battle_zmove
        modules = {'attack': (cmd_battle_attack, cmd_battle_attack.CmdBattleAttack),
                   'switch': (cmd_battle_switch, cmd_battle_switch.CmdBattleSwitch),
                   'item': (cmd_battle_item, cmd_battle_item.CmdBattleItem),
                   'concede': (cmd_battle_concede, cmd_battle_concede.CmdBattleConcede),
                   'tera': (cmd_battle_tera, cmd_battle_tera.CmdBattleTera),
                   'mega': (cmd_battle_mega, cmd_battle_mega.CmdBattleMega),
                   'zmove': (cmd_battle_zmove, cmd_battle_zmove.CmdBattleZMove)}
        module, cls = modules[kind]
        player = self.players[label]
        command = cls()
        command.caller, command.args, command.cmdstring = player, args, '+' + kind
        if kind == 'attack':
            command.parse()
        before = len(self.outputs[player.pk])
        if hasattr(module, 'get_system'):
            with patch.object(module, 'get_system', return_value=SimpleNamespace(battle_manager=None)):
                command.func()
        else:
            command.func()
        output = self.outputs[player.pk][before:]
        self.steps.append({'character': player.pk, 'input': '+' + kind + ' ' + args, 'output': output})
        return str(output)

    def rebuild(self):
        """Persist/discard runtime and restore exact ordinary character controllers."""
        old = self.session
        old.logic.sync_runtime_state()
        old.storage.set('data', old.data.to_dict())
        old.storage.set('state', old._compact_state_for_persist(old.state.to_dict()))
        old.logic = None
        self.session = BattleSession.restore(self.room, old.battle_id)
        return self.session

    def race(self, *actions):
        """Give every contender an independent guarded PostgreSQL connection."""
        from django.db import connections, connection
        barrier = Barrier(len(actions))
        def worker(action):
            """Close only the test thread's connection after the attempt."""
            try:
                connection.ensure_connection()
                with connection.cursor() as cursor:
                    cursor.execute('SELECT pg_backend_pid()')
                    pid = cursor.fetchone()[0]
                barrier.wait(timeout=10)
                try:
                    return pid, action()
                except ValueError as error:
                    return pid, str(error)
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            rows = list(pool.map(worker, actions))
        self.assertEqual(len({row[0] for row in rows}), len(actions))
        return [row[1] for row in rows]

    def lead_fixture(self, label, moves, *, species='Squirtle', ability='Torrent', held_item=''):
        """Separate staff prerequisite: install a native owned lead with known moves."""
        player = self.players[label]
        storage = existing_storage(player)
        old = storage.get_party_slots()[2]
        PlacementService(storage).to_box(old)
        mon = create_owned_pokemon(species, player.trainer, 20, nature='Hardy', ability=ability,
            ivs=[0] * 6, evs=[0] * 6, active_move_names=moves, held_item=held_item)
        PlacementService(storage).to_party(mon, 3)
        return mon

    def test_four_accounts_launch_exact_own_rosters_and_rebuild(self):
        """Team order cannot stand in for exact saved controller identity."""
        session = self.launch()
        for part in session.battle.participants:
            self.assertEqual(part.player.pk, self.players[part.field_position].pk)
            self.assertEqual(len(part.active), 1)
            self.assertEqual(len(part.pokemons), 2)
        before = {part.controller_id: (part.field_position, [mon.model_id for mon in part.pokemons]) for part in session.battle.participants}
        session.logic.sync_runtime_state()
        session.storage.set('data', session.data.to_dict())
        session.storage.set('state', session._compact_state_for_persist(session.state.to_dict()))
        session.logic = None
        self.session = BattleSession.restore(self.room, session.battle_id)
        self.assertIsNotNone(self.session)
        after = {part.controller_id: (part.field_position, [mon.model_id for mon in part.pokemons]) for part in self.session.battle.participants}
        self.assertEqual(before, after)
        self.assertEqual(len(self.session.trainers), 4)

    def test_normal_status_and_hud_show_four_controllers_with_exact_owner_privacy(self):
        """The real status command cannot fall back to two captain-owned actors."""
        from commands.player.cmd_effects import CmdEffects
        from pokemon.battle.interface import send_interface_to, broadcast_interfaces
        from pokemon.ui.battle_effects import render_effects_panel
        from evennia.utils.ansi import strip_ansi
        session = self.launch()
        viewer = self.players['A2']
        command = CmdEffects()
        command.caller, command.args = viewer, ''
        command.parse()
        start = len(self.outputs[viewer.pk])
        command.func()
        panel = strip_ansi(str(self.outputs[viewer.pk][start:]))
        self.steps.append({'character': viewer.pk, 'input': '+status', 'output': self.outputs[viewer.pk][start:]})
        for label, player in self.players.items():
            self.assertIn(f'{label}: {player.key}', panel)
        own = panel.split('A2: ')[1].split('B1: ')[0]
        partner = panel.split('A1: ')[1].split('A2: ')[0]
        self.assertIn('Ability: Torrent', own)
        self.assertIn('Ability: Unknown', partner)
        self.assertNotIn('Ability: Torrent', partner)
        mine = strip_ansi(render_effects_panel(session, viewer, focus='me'))
        self.assertIn('A2: ' + viewer.key, mine)
        self.assertNotIn('A1: ', mine)
        foes = strip_ansi(render_effects_panel(session, viewer, focus='opp'))
        self.assertIn('B1: ', foes)
        self.assertIn('B2: ', foes)
        self.assertNotIn('A2: ', foes)
        observer = strip_ansi(render_effects_panel(session, None))
        self.assertNotIn('Ability: Torrent', observer)
        start = len(self.outputs[viewer.pk])
        send_interface_to(session, viewer)
        broadcast_interfaces(session)
        hud = self.outputs[viewer.pk][start:]
        self.assertEqual(len(hud), 2)
        for block in hud:
            plain = strip_ansi(block)
            labels = {'A1': 'ALLY', 'A2': 'YOU', 'B1': 'FOE', 'B2': 'FOE'}
            headings = {}
            for label, role in labels.items():
                heading = re.search(rf'^{role}  [^\n]+ \({label}\)', plain, re.MULTILINE)
                self.assertIsNotNone(heading, plain)
                headings[label] = heading.start()
            for label, offset in headings.items():
                end = min((value for value in headings.values() if value > offset), default=len(plain))
                card = plain[offset:end]
                hp_line = next(line for line in card.splitlines() if line.startswith('HP ['))
                participant = next(part for part in session.battle.participants if part.field_position == label)
                if label == 'A2':
                    mon = participant.active[0]
                    self.assertIn(f'{mon.hp}/{mon.max_hp}', hp_line)
                else:
                    self.assertIn('Trainer: ' + self.players[label].key, card)
                    self.assertRegex(hp_line, r'\d+%$')
                    self.assertNotRegex(hp_line, r'\d+/\d+')
        for style in ('legacy', 'classic_modern', 'pf1'):
            viewer.db.battle_ui_style = style
            start = len(self.outputs[viewer.pk])
            send_interface_to(session, viewer)
            broadcast_interfaces(session)
            classic_hud = self.outputs[viewer.pk][start:]
            self.assertEqual(len(classic_hud), 2)
            for block in classic_hud:
                self.assertIn('A2: ' + viewer.key, block)
                self.assertIn('B2: ' + self.players['B2'].key, block)
                self.assertNotIn('=== Team A ===', block)
        part = next(part for part in session.battle.participants if part.player == viewer)
        part.active = []
        empty = strip_ansi(render_effects_panel(session, viewer, focus='me'))
        self.assertIn('Empty cell', empty)

    def test_four_independent_moves_resolve_once_and_spend_own_pp(self):
        """A team member's command cannot act for, replace or advance a teammate."""
        session = self.launch()
        self.assertIn('Choose your acting slot', self.command('A1', 'attack', 'A2 Tackle B1'))
        self.assertFalse(session.state.declare)
        for label, target in (('A1', 'B1'), ('A2', 'B2'), ('B1', 'A1')):
            self.command(label, 'attack', f'{label} Tackle {target}')
        before = deepcopy(dict(session.state.declare))
        self.command('A1', 'attack', 'A1 Water Gun B2')
        self.assertEqual(dict(session.state.declare), before)
        self.assertEqual(session.battle.turn_count, 1)
        self.command('B2', 'attack', 'B2 Tackle A2')
        self.assertFalse(session.turn_state.get('error'), session.turn_state)
        self.assertEqual(session.battle.turn_count, 2)
        self.assertFalse(session.state.declare)
        for part in session.battle.participants:
            mon = OwnedPokemon.objects.get(pk=part.pokemons[0].model_id.split(':')[1])
            self.assertEqual(mon.activemoveslot_set.get(slot=1).current_pp, 34)

    def test_saved_trainer_spoof_discards_only_wrong_choice(self):
        """Same team is insufficient authority for a saved declaration."""
        self.launch()
        self.command('A1', 'attack', 'A1 Tackle B1')
        self.command('A2', 'attack', 'A2 Tackle B2')
        self.session.state.declare['A1']['trainer'] = str(self.players['A2'].pk)
        session = self.rebuild()
        self.assertEqual(set(session.state.declare), {'A2'})
        part = next(part for part in session.battle.participants if part.field_position == 'A2')
        self.assertEqual(part.pending_action.pokemon.model_id, session.data.turndata.positions['A2'].pokemon.model_id)

    def test_second_controller_switches_only_own_gapped_reserve(self):
        """A2 stays A2; B2's targeted move hits its incoming own slot-six member."""
        session = self.launch()
        part = next(part for part in session.battle.participants if part.field_position == 'A2')
        reserve = part.pokemons[1]
        hp = reserve.hp
        self.command('A2', 'switch', 'A2 6')
        for label, target in (('A1', 'B1'), ('B1', 'A1'), ('B2', 'A2')):
            self.command(label, 'attack', f'{label} Tackle {target}')
        self.assertFalse(session.turn_state.get('error'), session.turn_state)
        self.assertIs(part.active[0], reserve)
        self.assertLess(reserve.hp, hp)
        self.assertIs(session.data.turndata.positions['A2'].pokemon, reserve)
        self.assertEqual(part.player.pk, self.players['A2'].pk)

    def test_shared_side_conditions_tick_once_and_rebuild_shared_sources(self):
        """Teammates share Reflect/hazards, while the opposing team stays separate."""
        session = self.launch()
        a1, a2 = [next(part for part in session.battle.participants if part.field_position == label) for label in ('A1', 'A2')]
        b1 = next(part for part in session.battle.participants if part.field_position == 'B1')
        self.assertIs(a1.side, a2.side)
        self.assertIsNot(a1.side, b1.side)
        a1.side.add_side_condition('reflect', {'duration': 3, 'target': a1.side, 'source': a1.active[0]})
        a1.side.set_hazard('spikes', 1)
        session.battle._handle_side_condition_durations()
        self.assertEqual(a2.side.conditions['reflect']['duration'], 2)
        self.assertFalse(b1.side.conditions)
        session = self.rebuild()
        a1, a2 = [next(part for part in session.battle.participants if part.field_position == label) for label in ('A1', 'A2')]
        self.assertIs(a1.side, a2.side)
        self.assertIs(a1.side.conditions['reflect']['target'], a1.side)
        self.assertIs(a1.side.conditions['reflect']['source'], a1.active[0])
        self.assertEqual(a1.side.hazards['spikes'], 1)

    def test_ally_only_move_rejects_foes_and_accepts_separate_controller(self):
        """Helping Hand uses allegiance without granting control of its recipient."""
        session = self.launch()
        self.command('A1', 'attack', 'A1 Helping Hand B1')
        self.assertFalse(session.state.declare)
        self.command('A1', 'attack', 'A1 Helping Hand A2')
        self.assertEqual(set(session.state.declare), {'A1'})
        a1 = next(part for part in session.battle.participants if part.field_position == 'A1')
        self.assertEqual(a1.pending_action.target.player.pk, self.players['A2'].pk)

    def test_empty_controller_slot_never_ends_team_or_owes_an_action(self):
        """An exhausted trainer cannot borrow its partner's reserves."""
        session = self.launch()
        part = next(part for part in session.battle.participants if part.field_position == 'A1')
        for mon in part.pokemons:
            mon.hp = 0
        session.battle.run_faint()
        session._sync_active_battle_state()
        self.assertIsNone(session.data.turndata.positions['A1'].pokemon)
        self.assertIsNone(session.battle.check_victory())
        self.assertNotIn('A1', session._missing_action_positions())
        session = self.rebuild()
        self.assertFalse(session.choices_for(self.players['A1']).positions())
        for label, target in (('A2', 'B1'), ('B1', 'A2'), ('B2', 'A2')):
            self.command(label, 'attack', f'{label} Tackle {target}')
        self.assertEqual(session.battle.turn_count, 2)
        self.assertFalse(session.turn_state.get('error'), session.turn_state)

    def test_concession_records_four_once_and_clears_all_controller_locks(self):
        """Normal confirmed concession uses existing PvP's no-prize/no-XP policy."""
        session = self.launch()
        reward_id = session.state.reward_id
        self.command('A2', 'concede', 'yes')
        from pokemon.services.battle_rewards import BattleRewards
        rows = []
        for label, player in self.players.items():
            receipt = BattleRewards.stored_attribute(player, BattleRewards(reward_id).key('multi-result'), category='battle_rewards')
            self.assertTrue(receipt['claimed'])
            self.assertEqual(receipt['payload']['outcome'], 'loss' if label.startswith('A') else 'win')
            self.assertEqual(receipt['payload']['money'], 0)
            self.assertFalse(BattleRewards.stored_attribute(player, 'battle_lock'))
            self.assertFalse(BattleRewards.stored_attribute(player, 'battle_id'))
            self.assertIsNone(player.ndb.battle_instance)
            rows.append(receipt)
        self.assertFalse(self.room.db.battles)

    def test_missing_unready_disconnected_and_expired_lobbies_fail_without_locks(self):
        """No pre-battle movement locks can strand members of an abandoned lobby."""
        from pokemon.battle.multi_lobby import MultiLobby
        from django.utils import timezone
        self.lobby('A1', 'create')
        self.assertIn('four slots', self.lobby('A1', 'start'))
        for label in ('A2', 'B1', 'B2'):
            self.lobby(label, 'join ' + label)
        for label in self.players:
            self.lobby(label, 'ready')
        with patch.object(self.players['B2'].sessions, 'all', return_value=[]):
            self.assertIn('connected', self.lobby('A1', 'start'))
        self.assertFalse(self.room.db.battles)
        future = timezone.now() + timedelta(minutes=11)
        self.assertIn('No open', MultiLobby(self.players['A1'], clock=lambda: future).status())
        for player in self.players.values():
            self.assertFalse(player.db.battle_lock)
            self.assertFalse(player.db.pvp_locked)

    def test_concurrent_join_and_duplicate_start_keep_one_complete_session(self):
        """Room serialization protects slot occupancy and all-four launch consent."""
        from pokemon.battle.multi_lobby import MultiLobby
        self.lobby('A1', 'create')
        results = self.race(lambda: MultiLobby(self.players['A2']).join('A2'),
                            lambda: MultiLobby(self.players['B1']).join('A2'))
        self.assertEqual(sum('already occupied' in str(row) for row in results), 1)
        saved = BattleRewards.stored_attribute(self.room, 'multi_pvp_lobby')
        winner = saved['members']['A2']['character']
        remaining = [player for label, player in self.players.items() if label != 'A1' and player.pk != winner]
        MultiLobby(remaining[0]).join('B1')
        MultiLobby(remaining[1]).join('B2')
        for player in self.players.values():
            MultiLobby(player).ready()
        rows = self.race(lambda: MultiLobby(self.players['A1']).start(), lambda: MultiLobby(self.players['A1']).start())
        sessions = [row for row in rows if isinstance(row, BattleSession)]
        self.assertEqual(len(sessions), 1)
        self.session = sessions[0]
        self.assertEqual(list(self.room.db.battles), [self.session.battle_id])
        self.assertEqual({part.player.pk for part in self.session.battle.participants}, {player.pk for player in self.players.values()})

    def test_startup_failure_rolls_back_lobby_consumption_and_all_partial_locks(self):
        """Failure after actual participant registration leaves the valid lobby retryable."""
        self.lobby('A1', 'create')
        for label in ('A2', 'B1', 'B2'):
            self.lobby(label, 'join ' + label)
        for label in self.players:
            self.lobby(label, 'ready')
        original = BattleSession._prepare_player_party
        def fault(session, player, *args, **kwargs):
            """Inject after extra controller registration, before full save."""
            if player.pk == self.players['A2'].pk:
                raise RuntimeError('Injected Multi launch fault')
            return original(session, player, *args, **kwargs)
        from pokemon.battle.multi_lobby import MultiLobby
        with patch.object(BattleSession, '_prepare_player_party', fault):
            with self.assertRaisesRegex(RuntimeError, 'launch fault'):
                MultiLobby(self.players['A1']).start()
        self.assertTrue(BattleRewards.stored_attribute(self.room, 'multi_pvp_lobby'))
        self.assertFalse(BattleRewards.stored_attribute(self.room, 'battles'))
        for player in self.players.values():
            self.assertFalse(BattleRewards.stored_attribute(player, 'battle_lock'))
            self.assertFalse(BattleRewards.stored_attribute(player, 'battle_id'))
            self.assertIsNone(player.ndb.battle_instance)
        self.session = MultiLobby(self.players['A1']).start()
        self.assertEqual(len(self.session.battle.participants), 4)

    def test_checkpoint_fault_restores_four_exact_controllers_and_retained_turn(self):
        """SQL and runtime rollback preserve every valid teammate choice and own PP."""
        session = self.launch()
        initial = {part.controller_id: [mon.model_id for mon in part.pokemons] for part in session.battle.participants}
        for label, target in (('A1', 'B1'), ('A2', 'B2'), ('B1', 'A1')):
            self.command(label, 'attack', f'{label} Tackle {target}')
        original, fired = session.storage.set, []
        def fault(part, value):
            """Fail after the real checkpoint write inside the turn transaction."""
            original(part, value)
            if part == 'data' and session.battle.turn_count >= 2 and not fired:
                fired.append(True)
                raise RuntimeError('Injected four-controller checkpoint fault')
        with patch.object(session.storage, 'set', side_effect=fault):
            self.command('B2', 'attack', 'B2 Tackle A2')
        self.assertTrue(fired)
        self.assertTrue(session.turn_state.get('error'))
        self.assertEqual(session.battle.turn_count, 1)
        self.assertEqual(set(session.state.declare), {'A1', 'A2', 'B1', 'B2'})
        self.assertEqual({part.controller_id: [mon.model_id for mon in part.pokemons] for part in session.battle.participants}, initial)
        for part in session.battle.participants:
            self.assertEqual(str(part.player.pk), part.controller_id)
            row = OwnedPokemon.objects.get(pk=part.pokemons[0].model_id.split(':')[1])
            self.assertEqual(row.activemoveslot_set.get(slot=1).current_pp, 35)
        session.maybe_run_turn()
        self.assertEqual(session.battle.turn_count, 2)
        self.assertFalse(session.turn_state.get('error'), session.turn_state)

    def test_shared_tera_reservation_rejects_teammate_cancel_and_survives_rebuild(self):
        """One shared team budget retains exact actor ownership and cancellation."""
        session = self.launch()
        a1, a2 = self.players['A1'], self.players['A2']
        session.choices_for(a1).tera(actor='A1')
        old = deepcopy(session.battle.tera_pending)
        with self.assertRaises(ValueError):
            session.choices_for(a2).tera(actor='A2')
        with self.assertRaises(ValueError):
            session.choices_for(a2).tera(actor='A2', cancel=True)
        self.assertEqual(session.battle.tera_pending, old)
        session = self.rebuild()
        self.assertEqual(session.battle.tera_pending, old)
        session.choices_for(a1).switch('6', actor='A1')
        self.assertFalse(session.battle.tera_pending)
        session.choices_for(a2).tera(actor='A2')
        for label, target in (('A2', 'B2'), ('B1', 'A1'), ('B2', 'A2')):
            self.command(label, 'attack', f'{label} Tackle {target}')
        self.assertIn('A', session.battle.tera_used)
        self.assertNotIn('B', session.battle.tera_used)
        self.assertFalse(session.battle.tera_pending)
        with self.assertRaises(ValueError):
            session.choices_for(a1).tera(actor='A1')

    def test_spread_move_hits_foes_and_teammate_without_hitting_its_user(self):
        """Normal Surf plus separate-controller Helping Hand uses actual recipients."""
        session = self.launch()
        initial = {part.field_position: part.active[0].hp for part in session.battle.participants}
        self.command('A1', 'attack', 'A1 Surf')
        self.command('A2', 'attack', 'A2 Helping Hand A1')
        self.command('B1', 'attack', 'B1 Helping Hand B2')
        self.command('B2', 'attack', 'B2 Helping Hand B1')
        self.assertEqual(session.battle.turn_count, 2)
        self.assertFalse(session.turn_state.get('error'), session.turn_state)
        for part in session.battle.participants:
            if part.field_position == 'A1':
                self.assertEqual(part.active[0].hp, initial['A1'])
            else:
                self.assertLess(part.active[0].hp, initial[part.field_position])

    def test_single_team_timeout_and_both_team_timeout_use_durable_outcomes(self):
        """Timer policy ends missing actions without resetting on reconnect."""
        from django.utils import timezone
        from pokemon.battle.multi_battle import check_timeout
        session = self.launch()
        deadline = session.state.multi['deadline']
        for label, target in (('A1', 'B1'), ('B1', 'A1'), ('B2', 'A2')):
            self.command(label, 'attack', f'{label} Tackle {target}')
        session = self.rebuild()
        self.assertEqual(session.state.multi['deadline'], deadline)
        reward_id = session.state.reward_id
        self.assertTrue(check_timeout(session, now=timezone.now() + timedelta(minutes=6)))
        for label, player in self.players.items():
            receipt = BattleRewards.stored_attribute(player, BattleRewards(reward_id).key('multi-result'), category='battle_rewards')
            self.assertEqual(receipt['payload']['outcome'], 'loss' if label.startswith('A') else 'win')

    def test_both_overdue_teams_draw_and_pending_receipts_retry_before_cleanup(self):
        """Claim faults retain all four terminal receipts and locks until retry."""
        from django.utils import timezone
        from pokemon.battle.multi_battle import check_timeout
        session = self.launch()
        reward_id = session.state.reward_id
        with patch.object(BattleRewards, 'claim', side_effect=RuntimeError('Injected claim fault')):
            with self.assertRaisesRegex(RuntimeError, 'claim fault'):
                check_timeout(session, now=timezone.now() + timedelta(minutes=6))
        self.assertTrue(session.state.multi['result'])
        for player in self.players.values():
            self.assertTrue(BattleRewards.stored_attribute(player, 'battle_lock'))
            row = BattleRewards.stored_attribute(player, BattleRewards(reward_id).key('multi-result'), category='battle_rewards')
            self.assertFalse(row['claimed'])
        session.end()
        for player in self.players.values():
            row = BattleRewards.stored_attribute(player, BattleRewards(reward_id).key('multi-result'), category='battle_rewards')
            self.assertTrue(row['claimed'])
            self.assertEqual(row['payload']['outcome'], 'draw')
            self.assertFalse(BattleRewards.stored_attribute(player, 'battle_lock'))

    def test_current_owned_item_route_cannot_borrow_partner_inventory_or_target(self):
        """Normal +item consumes only the acting controller's own usable stock."""
        session = self.launch()
        part = next(part for part in session.battle.participants if part.field_position == 'A2')
        part.active[0].hp = 2
        self.players['A2'].trainer.add_item('Potion', 1)
        self.command('A1', 'item', 'A1 Potion=3')
        self.assertFalse(session.state.declare)
        self.command('A2', 'item', 'A2 Potion=A1')
        self.assertFalse(session.state.declare)
        self.command('A2', 'item', 'A2 Potion=3')
        self.assertEqual(set(session.state.declare), {'A2'})
        for label, target in (('A1', 'B1'), ('B1', 'A1'), ('B2', 'A2')):
            self.command(label, 'attack', f'{label} Tackle {target}')
        self.assertEqual(session.battle.turn_count, 2)
        self.assertFalse(session.turn_state.get('error'), session.turn_state)
        self.assertEqual(self.players['A2'].trainer.get_item_quantity('Potion'), 0)
        self.assertEqual(self.players['A1'].trainer.get_item_quantity('Potion'), 0)

    def test_same_account_alt_and_raw_account_controller_are_refused(self):
        """Playable-character and account ID domains never become interchangeable."""
        from pokemon.battle.multi_lobby import MultiLobby
        alt = fixtures.character(account=self.players['A1'].account)
        alt.location = self.room
        self.lobby('A1', 'create')
        with self.assertRaisesRegex(ValueError, 'distinct player accounts'):
            MultiLobby(alt).join('A2')
        self.lobby('A1', 'leave')
        session = self.launch()
        from copy import copy
        raw_account = copy(self.players['B1'].account)
        raw_account.pk = self.players['A1'].pk
        before = deepcopy(dict(session.state.declare))
        with self.assertRaises(ValueError):
            session.choices_for(raw_account)
        self.assertEqual(dict(session.state.declare), before)

    def test_concurrent_choices_preserve_both_controllers_and_stale_turn_cannot_replay(self):
        """Competing declarations merge under the room lock or reject without loss."""
        session = self.launch()
        def submit(label, target):
            """Retry once after an explicitly stale checkpoint rejection."""
            for attempt in range(2):
                try:
                    return session.choices_for(self.players[label]).move('Tackle', target, actor=label)
                except ValueError:
                    if attempt:
                        raise
        rows = self.race(lambda: submit('A1', 'B1'), lambda: submit('A2', 'B2'))
        current = self.players['A1'].ndb.battle_instance
        self.session = current
        saved = BattleRewards.stored_attribute(self.room, current.storage._key('state'))
        self.assertEqual(set(saved['declare']), {'A1', 'A2'})
        self.command('B1', 'attack', 'B1 Tackle A1')
        self.command('B2', 'attack', 'B2 Tackle A2')
        self.assertEqual(current.battle.turn_count, 2)
        self.assertFalse(current.turn_state.get('error'), current.turn_state)
        # Reuse the pre-turn persisted input as an obsolete independent session.
        from copy import copy
        from pokemon.battle.logic import BattleLogic
        old = copy(current)
        stale_state = dict(saved)
        stale_data = current.data.to_dict()
        stale_data['battle']['turn'] = 1
        old.logic = BattleLogic.from_dict({'state': stale_state, 'data': stale_data})
        from pokemon.battle.multi_state import attach_players
        attach_players(old)
        before = list(OwnedPokemon.objects.filter(trainer__user_id__in=[p.pk for p in self.players.values()]).values('pk', 'current_hp'))
        with self.assertRaises(ValueError):
            old.execute_persistent_turn()
        after = list(OwnedPokemon.objects.filter(trainer__user_id__in=[p.pk for p in self.players.values()]).values('pk', 'current_hp'))
        self.assertEqual(before, after)

    def test_reflect_effect_and_wide_guard_cover_both_teammates_only(self):
        """Actual hit pipeline plus side-shield checks have positive and foe controls."""
        from pokemon.battle.engine import Action, ActionType, BattleMove
        from pokemon.dex import MOVEDEX
        from pokemon.names import resolve_dex_entry
        session = self.launch()
        battle = session.battle
        parts = {part.field_position: part for part in battle.participants}
        attacker = parts['B1']
        def hit(label):
            """Use identical per-engine RNG for baseline and guarded target hits."""
            target = parts[label].active[0]
            target.hp = target.max_hp
            battle.rng = random.Random(71)
            move = BattleMove('Tackle', key='tackle', power=40, pp=35, type='Normal', accuracy=100,
                             raw={'name': 'Tackle', 'basePower': 40, 'category': 'Physical', 'type': 'Normal', 'target': 'normal'})
            battle.use_move(Action(attacker, ActionType.MOVE, parts[label], move=move,
                                   pokemon=attacker.active[0], target_pokemon=target, target_slot=0))
            return target.max_hp - target.hp
        baseline = hit('A1')
        battle.use_move(Action(parts['A1'], ActionType.MOVE, parts['A1'], move=BattleMove('Reflect'),
                               pokemon=parts['A1'].active[0], target_pokemon=parts['A1'].active[0]))
        self.assertGreater(baseline, 0)
        self.assertLess(hit('A1'), baseline)
        self.assertLess(hit('A2'), baseline)
        self.assertEqual(hit('B2'), baseline)
        battle.use_move(Action(parts['A1'], ActionType.MOVE, parts['A1'], move=BattleMove('Wide Guard'),
                               pokemon=parts['A1'].active[0], target_pokemon=parts['A1'].active[0]))
        raw = resolve_dex_entry(MOVEDEX, 'Surf').raw
        surf = BattleMove('Surf', key='surf', raw=raw, power=90, type='Water', pp=15)
        self.assertFalse(battle._passes_side_protection(parts['A2'].active[0], attacker.active[0], surf))
        self.assertTrue(battle._passes_side_protection(parts['B2'].active[0], parts['A1'].active[0], surf))

    def test_follow_me_redirects_foe_attack_to_the_other_controller(self):
        """A teammate's redirect is shared allegiance, not ownership of its target."""
        self.lead_fixture('A2', ['Follow Me', 'Tackle', 'Helping Hand', 'Protect'])
        session = self.launch()
        parts = {part.field_position: part for part in session.battle.participants}
        before = {label: part.active[0].hp for label, part in parts.items()}
        self.command('A1', 'attack', 'A1 Helping Hand A2')
        self.command('A2', 'attack', 'A2 Follow Me')
        self.command('B1', 'attack', 'B1 Tackle A1')
        self.command('B2', 'attack', 'B2 Helping Hand B1')
        self.assertFalse(session.turn_state.get('error'), session.turn_state)
        self.assertEqual(session.battle.turn_count, 2)
        self.assertEqual(parts['A1'].active[0].hp, before['A1'])
        self.assertLess(parts['A2'].active[0].hp, before['A2'])

    def test_follow_me_preserves_opposing_screen_and_its_teammates_attack_target(self):
        """A redirector cannot steal a side move or its own teammate's attack."""
        self.lead_fixture('A1', ['Reflect', 'Tackle', 'Helping Hand', 'Protect'])
        self.lead_fixture('B2', ['Follow Me', 'Tackle', 'Helping Hand', 'Protect'])
        session = self.launch()
        parts = {part.field_position: part for part in session.battle.participants}
        before = {label: part.active[0].hp for label, part in parts.items()}
        for label, move in (('A1', 'Reflect'), ('A2', 'Helping Hand A1'),
                            ('B1', 'Tackle A2'), ('B2', 'Follow Me')):
            self.command(label, 'attack', label + ' ' + move)
        self.assertFalse(session.turn_state.get('error'), session.turn_state)
        self.assertEqual(session.battle.turn_count, 2)
        self.assertIn('reflect', parts['A1'].side.conditions)
        self.assertLess(parts['A2'].active[0].hp, before['A2'])
        self.assertEqual(parts['B2'].active[0].hp, before['B2'])
        self.assertNotIn('followme', parts['B2'].active[0].volatiles)
        before_second = {label: part.active[0].hp for label, part in parts.items()}
        for label, move in (('A1', 'Helping Hand A2'), ('A2', 'Tackle B1'),
                            ('B1', 'Tackle A2'), ('B2', 'Tackle A1')):
            self.command(label, 'attack', label + ' ' + move)
        self.assertEqual(session.battle.turn_count, 3)
        self.assertLess(parts['B1'].active[0].hp, before_second['B1'])
        self.assertEqual(parts['B2'].active[0].hp, before_second['B2'])

    def test_rage_powder_uses_four_controller_shape_and_expires_after_one_turn(self):
        """The other existing redirection move uses the same Multi shape/timing."""
        self.lead_fixture('B2', ['Rage Powder', 'Tackle', 'Helping Hand', 'Protect'])
        session = self.launch()
        parts = {part.field_position: part for part in session.battle.participants}
        before = {label: part.active[0].hp for label, part in parts.items()}
        for label, move in (('A1', 'Tackle B1'), ('A2', 'Helping Hand A1'),
                            ('B1', 'Tackle A2'), ('B2', 'Rage Powder')):
            self.command(label, 'attack', label + ' ' + move)
        self.assertFalse(session.turn_state.get('error'), session.turn_state)
        self.assertEqual(session.battle.turn_count, 2)
        self.assertEqual(parts['B1'].active[0].hp, before['B1'])
        self.assertLess(parts['B2'].active[0].hp, before['B2'])
        self.assertLess(parts['A2'].active[0].hp, before['A2'])
        self.assertNotIn('ragepowder', parts['B2'].active[0].volatiles)

    def test_follow_me_does_not_collapse_spread_move_recipients(self):
        """Surf still hits both foes and its adjacent teammate under Follow Me."""
        self.lead_fixture('A1', ['Reflect', 'Tackle', 'Helping Hand', 'Protect'])
        self.lead_fixture('B2', ['Follow Me', 'Tackle', 'Helping Hand', 'Protect'])
        session = self.launch()
        parts = {part.field_position: part for part in session.battle.participants}
        before = {label: part.active[0].hp for label, part in parts.items()}
        for label, move in (('A1', 'Reflect'), ('A2', 'Helping Hand A1'),
                            ('B1', 'Surf'), ('B2', 'Follow Me')):
            self.command(label, 'attack', label + ' ' + move)
        self.assertFalse(session.turn_state.get('error'), session.turn_state)
        self.assertEqual(session.battle.turn_count, 2)
        for label in ('A1', 'A2', 'B2'):
            self.assertLess(parts[label].active[0].hp, before[label])
        self.assertEqual(parts['B1'].active[0].hp, before['B1'])

    def test_ally_switch_moves_physical_positions_without_transferring_control(self):
        """The attack follows its chosen cell; each Pokemon retains its controller."""
        self.lead_fixture('A1', ['Ally Switch', 'Tackle', 'Helping Hand', 'Protect'])
        session = self.launch()
        original = {part.controller_id: part for part in session.battle.participants}
        a1 = original[str(self.players['A1'].pk)]
        a2 = original[str(self.players['A2'].pk)]
        hp = a2.active[0].hp
        self.command('A1', 'attack', 'A1 Ally Switch')
        self.command('A2', 'attack', 'A2 Helping Hand A1')
        self.command('B1', 'attack', 'B1 Tackle A1')
        self.command('B2', 'attack', 'B2 Helping Hand B1')
        self.assertEqual(session.battle.turn_count, 2)
        self.assertFalse(session.turn_state.get('error'), session.turn_state)
        self.assertEqual((a1.field_position, a2.field_position), ('A2', 'A1'))
        self.assertLess(a2.active[0].hp, hp)
        messages = str(self.outputs[self.players['A1'].pk])
        self.assertIn('used Ally Switch!', messages)
        self.assertNotIn('Trick Room', messages)
        self.assertEqual(set(session.choices_for(self.players['A1']).positions()), {'A2'})
        session = self.rebuild()
        self.assertEqual(set(session.choices_for(self.players['A1']).positions()), {'A2'})

    def test_mega_and_z_team_reservations_never_replace_partner_input(self):
        """Existing enabled mechanics keep separate per-team budgets and owners."""
        self.lead_fixture('A1', ['Tackle', 'Helping Hand'], species='Mawile', ability='Intimidate', held_item='Mawilite')
        self.lead_fixture('A2', ['Tackle', 'Helping Hand'], species='Absol', ability='Super Luck', held_item='Absolite')
        self.lead_fixture('B1', ['Tackle', 'Helping Hand'], species='Eevee', ability='Run Away', held_item='Normalium Z')
        self.lead_fixture('B2', ['Tackle', 'Helping Hand'], species='Pikachu', ability='Static', held_item='Normalium Z')
        session = self.launch()
        self.command('A1', 'mega', 'A1')
        old = deepcopy(session.battle.mega_pending)
        self.command('A2', 'mega', 'A2')
        self.command('A2', 'mega', 'A2 cancel')
        self.assertEqual(session.battle.mega_pending, old)
        self.assertIn('A', old)
        self.command('B1', 'zmove', 'B1 Tackle=A1')
        old_z = deepcopy(session.battle.z_pending)
        self.command('B2', 'zmove', 'B2 Tackle=A2')
        self.assertEqual(session.battle.z_pending, old_z)
        self.assertIn('B', old_z)
        self.assertEqual(set(session.state.declare), {'B1'})
        session = self.rebuild()
        self.assertEqual(session.battle.mega_pending, old)
        self.assertEqual(session.battle.z_pending, old_z)

    def test_forced_replacement_uses_only_its_controller_and_retains_partner_slot(self):
        """One faint replaces its own lead; a partner's reserve is never eligible."""
        session = self.launch()
        parts = {part.field_position: part for part in session.battle.participants}
        partner = parts['A2'].active[0]
        incoming = parts['A1'].pokemons[1]
        parts['A1'].active[0].hp = 0
        session.battle.run_faint()
        session._sync_active_battle_state()
        self.assertIs(parts['A1'].active[0], incoming)
        self.assertIs(parts['A2'].active[0], partner)
        self.assertIs(session.data.turndata.positions['A1'].pokemon, incoming)
        self.assertIs(session.data.turndata.positions['A2'].pokemon, partner)
        self.assertNotIn(incoming, parts['A2'].pokemons)

    def test_full_party_and_reserved_fusion_keep_seven_own_switch_choices(self):
        """Combined team serialization never truncates a trainer's seventh Fusion."""
        player = self.players['A1']
        storage = existing_storage(player)
        for slot in (1, 2, 4, 5):
            mon = create_owned_pokemon('Eevee', player.trainer, 20, nature='Hardy', ivs=[0] * 6, evs=[0] * 6,
                ability='Run Away', active_move_names=['Tackle'])
            PlacementService(storage).to_party(mon, slot)
        fused = create_owned_pokemon('Charmander', player.trainer, 20, nature='Hardy', ivs=[0] * 6, evs=[0] * 6,
            ability='Blaze', active_move_names=['Tackle'])
        PlacementService(storage).reserve_for_fusion(fused)
        player.db.fusion_id, player.db.fusion_kind = str(fused.pk), 'permanent'
        player.db.fusion_forms, player.db.fighter_xp = [str(fused.pk)], fused.total_exp
        session = self.launch()
        own = next(part for part in session.battle.participants if part.player.pk == player.pk)
        self.assertEqual(len(own.pokemons), 7)
        self.assertIn('fusion', session.choices_for(player).switch_choices())
        self.command('A2', 'attack', 'A2 Tackle B2')
        self.command('A1', 'switch', 'A1 fusion')
        self.assertEqual(set(session.state.declare), {'A1', 'A2'})
        session = self.rebuild()
        own = next(part for part in session.battle.participants if part.player.pk == player.pk)
        self.assertEqual(len(own.pokemons), 7)
        self.assertEqual(own.pending_action.pokemon.model_id, 'owned:' + str(fused.pk))
        self.assertEqual(set(session.state.declare), {'A1', 'A2'})

    def test_foreign_or_newly_reserved_roster_refuses_without_overwriting_partner(self):
        """Fresh native ownership/claim guards apply to ordinary Multi input too."""
        from pokemon.models.ownership import PokemonReservation
        session = self.launch()
        own = next(part for part in session.battle.participants if part.field_position == 'A1')
        identity = own.active[0].model_id.split(':')[1]
        self.command('A2', 'attack', 'A2 Tackle B2')
        before = deepcopy(dict(session.state.declare))
        reservation = PokemonReservation.objects.create(pokemon_id=identity, storage=existing_storage(self.players['A1']),
            kind='market', token=uuid4())
        self.command('A1', 'attack', 'A1 Tackle B1')
        self.assertEqual(dict(session.state.declare), before)
        reservation.delete()
        trainer_id = self.players['A1'].trainer.pk
        OwnedPokemon.objects.filter(pk=identity).update(trainer_id=self.players['B1'].trainer.pk)
        try:
            self.command('A1', 'attack', 'A1 Tackle B1')
            self.assertEqual(dict(session.state.declare), before)
        finally:
            OwnedPokemon.objects.filter(pk=identity).update(trainer_id=trainer_id)

    def test_normal_final_round_records_team_win_and_all_four_cleanup_once(self):
        """Actual four inputs reach team exhaustion and durable end without debug launch."""
        session = self.launch()
        reward_id = session.state.reward_id
        for part in session.battle.participants:
            if part.team == 'B':
                for index, mon in enumerate(part.pokemons):
                    mon.hp = 1 if index == 0 else 0
                    OwnedPokemon.objects.filter(pk=mon.model_id.split(':')[1]).update(current_hp=mon.hp)
        for label, move, target in (('A1', 'Tackle', 'B1'), ('A2', 'Tackle', 'B2'),
                                     ('B1', 'Helping Hand', 'B2'), ('B2', 'Helping Hand', 'B1')):
            self.command(label, 'attack', f'{label} {move} {target}')
        self.assertIsNone(session.logic, session.turn_state)
        self.assertFalse(self.room.db.battles)
        for label, player in self.players.items():
            row = BattleRewards.stored_attribute(player, BattleRewards(reward_id).key('multi-result'), category='battle_rewards')
            self.assertEqual(row['payload']['outcome'], 'win' if label.startswith('A') else 'loss')
            self.assertTrue(row['claimed'])
            self.assertFalse(BattleRewards.stored_attribute(player, 'battle_lock'))
            self.assertIsNone(player.ndb.battle_instance)
        # Cleanup/claim replay cannot add any resources or recreate a battle.
        session.end()
        self.assertFalse(self.room.db.battles)

    def test_room_timer_prunes_departed_members_and_clears_remaining_readiness(self):
        """Leaving the room cannot leave a stale ready consent behind."""
        from evennia.scripts.models import ScriptDB
        self.lobby('A1', 'create')
        self.lobby('A2', 'join A2')
        self.lobby('A1', 'ready')
        self.lobby('A2', 'ready')
        watch = ScriptDB.objects.get(db_key='multi-pvp-watch-' + str(self.room.pk))
        self.assertEqual(watch.interval, 30)
        self.players['A2'].location = None
        watch.at_repeat()
        saved = BattleRewards.stored_attribute(self.room, 'multi_pvp_lobby')
        self.assertEqual(set(saved['members']), {'A1'})
        self.assertFalse(saved['members']['A1']['ready'])
        self.players['A1'].location = None
        watch.at_repeat()
        self.assertFalse(BattleRewards.stored_attribute(self.room, 'multi_pvp_lobby'))

    def test_combined_native_host_rejects_lobby_before_battle_or_asset_locks(self):
        """The new native slice cannot silently enter four-controller Multi."""
        from pokemon.services.necrozma import NecrozmaService
        from pokemon.models.necrozma import NecrozmaCombination

        self.room.attributes.add('is_pokemon_center', True)
        player = self.players['A1']
        host = create_owned_pokemon('Necrozma', player.trainer, 50, ability='Prism Armor', ivs=[0]*6, evs=[0]*6)
        companion = create_owned_pokemon('Solgaleo', player.trainer, 50, ability='Full Metal Body', ivs=[0]*6, evs=[0]*6)
        service = NecrozmaService(player)
        operation = service.prepare('combine', str(host.pk), str(companion.pk), 2)
        service.commit(operation.pk)
        output = self.lobby('A1', 'create')
        self.assertIn('Separate your native Necrozma', output)
        self.assertFalse(BattleRewards.stored_attribute(self.room, 'multi_pvp_lobby'))
        self.assertTrue(NecrozmaCombination.objects.filter(host=host, companion=companion).exists())
        for other in self.players.values():
            self.assertFalse(BattleRewards.stored_attribute(other, 'battle_lock'))
            self.assertIsNone(other.ndb.battle_instance)


if __name__ == '__main__':
    with IsolatedPostgres() as database:
        database.create_model_tables()
        from django.apps import apps
        from django.contrib.contenttypes.models import ContentType
        ContentType.objects.get_for_models(*apps.get_models(), for_concrete_models=False)
        with OrdinaryPlayerFixtures('october-multi-qa') as fixtures:
            from evennia.objects.models import ObjectDB
            from evennia.accounts.models import AccountDB
            from pokemon.helpers.pokemon_helpers import create_owned_pokemon
            from pokemon.models.core import OwnedPokemon
            from pokemon.services.placement import PlacementService
            from utils.character_reads import existing_storage
            from commands.player.cmd_pvp_multi import CmdPvpMulti
            from pokemon.battle.battleinstance import BattleSession
            from pokemon.services.battle_rewards import BattleRewards
            result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(MultiBattleCases))
            if os.environ.get('PF2_MULTI_PLAYER_EVIDENCE'):
                Path(os.environ['PF2_MULTI_PLAYER_EVIDENCE']).write_text(json.dumps(TRANSCRIPT, indent=2), encoding='utf-8')
            raise SystemExit(not result.wasSuccessful())

"""Database-backed reward failures and real battle-session rebuild checks."""

from __future__ import annotations

import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
from ui_cases import PlayerView


class BattleRecoveryCases(unittest.TestCase):
    """Drive production sessions against disposable PostgreSQL model tables."""

    def setUp(self):
        """Create two ordinary players, a real room and a two-member NPC roster."""
        self.players = []
        room = ObjectDB.objects.create(db_key="Recovery room " + uuid4().hex[:8])
        self.room = SimpleNamespace(id=room.pk, pk=room.pk, key=room.key, db=room.db, ndb=room.ndb,
                                    attributes=room.attributes, contents=[])
        for name in ("Recovery A ", "Recovery B "):
            character = ObjectDB.objects.create(db_key=name + uuid4().hex[:8])
            trainer = Trainer.objects.create(user=character, trainer_number=Trainer.objects.count() + 1)
            storage = UserStorage.objects.create(user=character)
            player = PlayerView(character, trainer, storage)
            # Native post-battle item cleanup uses the same primary-key alias
            # exposed by real Evennia objects, including on its rollback path.
            player.pk = character.pk
            player.location = self.room
            self.players.append(player)
            self.room.contents.append(player)
            for species in ("Squirtle", "Bulbasaur"):
                create_owned_pokemon(species, trainer, 5, ivs=[0] * 6, evs=[0] * 6,
                                     nature="Hardy", active_move_names=["Tackle"])
        self.player = self.players[0]
        self.npc = NPCTrainer.objects.create(name="Recovery NPC " + uuid4().hex[:8])
        for order, species in enumerate(("Rattata", "Pidgey"), 1):
            NPCPokemonTemplate.objects.create(npc_trainer=self.npc, species=species, level=3,
                                              template_key=str(order), sort_order=order,
                                              ivs=[0] * 6, evs=[0] * 6, move_names=["Tackle"])
        self.sessions = []
        self.search = patch("pokemon.battle.battleinstance.search_object", self.find)
        self.search.start()

    def tearDown(self):
        """Clean only the current restored session for each test battle."""
        self.search.stop()
        for session in self.sessions:
            if session.battle_id in (self.room.db.battles or []):
                session.end()

    def find(self, query):
        """Resolve transport wrappers while leaving all persistence real."""
        return [p for p in self.players if query == f"#{p.id}"]

    def start(self, kind="npc"):
        """Start the ordinary NPC, wild or two-player session implementation."""
        for player in self.players:
            for mon in OwnedPokemon.objects.filter(trainer=player.trainer):
                mon.current_hp = get_max_hp(mon)
                mon.save(update_fields=("current_hp",))
        session = BattleSession(self.player, self.players[1] if kind == "pvp" else None)
        if kind in {"npc", "double"}:
            encounter = generate_static_trainer_encounter(self.npc)
            if kind == "double":
                encounter = replace(encounter, battle_format="double")
            session.start_trainer_encounter(encounter)
        elif kind == "wild":
            mon = create_battle_pokemon("Rattata", 3, is_wild=True, move_names=["Tackle"])
            session._track_temp_opponent_team([mon])
            session._select_opponent = lambda: (mon, "Wild Rattata", BattleType.WILD, "Wild encounter")
            session.start()
        else:
            session.start()
        self.sessions.append(session)
        return session

    def rebuild(self, session):
        """Discard live references and restore the production serialized checkpoint."""
        session._sync_active_battle_state()
        session._persist_turn_state()
        battle_handler.unregister(session)
        for player in self.players:
            player.ndb.battle_instance = None
        self.room.ndb.battle_instances = {}
        restored = BattleSession.restore(self.room, session.battle_id)
        self.assertIsNotNone(restored)
        self.sessions[self.sessions.index(session)] = restored
        return restored

    def wallet(self):
        """Read the authoritative wallet without a cached trainer instance."""
        return Trainer.objects.values_list("money", flat=True).get(pk=self.player.trainer.pk)

    def exp(self):
        """Read the complete party EXP vector directly from SQL."""
        return list(OwnedPokemon.objects.filter(trainer=self.player.trainer).order_by("pk")
                    .values_list("total_exp", flat=True))

    def defeat_npc(self, session):
        """Reach the normal terminal reward path with both configured opponents fainted."""
        for mon in session.battle.participants[1].pokemons:
            mon.hp = 0
        session.battle.run_faint()
        return session.battle.participants[0]

    def test_failed_wallet_write_does_not_announce_or_mark_delivery(self):
        """A write outage must remain retryable instead of claiming successful payment."""
        session = self.start()
        winner = self.defeat_npc(session)
        before = self.wallet()
        with patch.object(Trainer, "add_money", side_effect=RuntimeError("wallet unavailable")):
            try:
                session.battle.handle_end_of_battle_rewards(winner)
            except RuntimeError:
                pass
        self.assertFalse(session.battle._rewards_granted)
        self.assertEqual(self.wallet(), before)
        self.assertFalse(any("received ₽" in str(message) for message in self.player.messages))
        session.battle.handle_end_of_battle_rewards(winner)
        self.assertGreater(self.wallet(), before)

    def test_prize_replay_after_rebuild_pays_once(self):
        """A fresh engine cannot turn an already committed prize into a new payment."""
        session = self.start()
        winner = self.defeat_npc(session)
        session.battle.handle_end_of_battle_rewards(winner)
        paid = self.wallet()
        self.assertGreater(paid, 0)
        restored = self.rebuild(session)
        restored.battle.participants[1].has_lost = True
        restored.battle.handle_end_of_battle_rewards(restored.battle.participants[0])
        self.assertEqual(self.wallet(), paid)

    def test_faint_rebuild_does_not_repeat_exp_or_evs(self):
        """A previously processed faint must not award EXP again when rebuilt."""
        session = self.start()
        session.battle.participants[1].active[0].hp = 0
        session.battle.run_faint()
        awarded = self.exp()
        restored = self.rebuild(session)
        restored.battle.run_faint()
        self.assertEqual(self.exp(), awarded)
        self.assertEqual(restored.battle.participants[1].active[0].name, "Pidgey")

    def test_no_reserve_rebuild_has_no_fainted_active(self):
        """All-fainted teams must stay terminal rather than restoring an invalid lead."""
        for kind in ("npc", "wild", "pvp"):
            with self.subTest(kind=kind):
                session = self.start(kind)
                for mon in session.battle.participants[0].pokemons:
                    mon.hp = 0
                session.battle.run_faint()
                restored = self.rebuild(session)
                part = restored.battle.participants[0]
                self.assertFalse(part.active)
                self.assertTrue(part.has_lost)
                restored.end()

    def test_forced_reserve_rebuild_uses_conscious_member(self):
        """Fainting and restoring retain the legal player reserve in each battle type."""
        for kind in ("npc", "wild", "pvp"):
            with self.subTest(kind=kind):
                session = self.start(kind)
                part = session.battle.participants[0]
                part.active[0].hp = 0
                session.battle.run_faint()
                restored = self.rebuild(session)
                active = restored.battle.participants[0].active
                self.assertEqual(len(active), 1)
                self.assertGreater(active[0].hp, 0)
                self.assertEqual(active[0].name, "Bulbasaur")
                restored.end()

    def test_pvp_rebuild_keeps_both_sides_human(self):
        """A restored opponent must still wait for its player's action."""
        restored = self.rebuild(self.start("pvp"))
        self.assertEqual(restored.battle.type, BattleType.PVP)
        self.assertFalse(restored.battle.participants[0].is_ai)
        self.assertFalse(restored.battle.participants[1].is_ai)

    def test_wallet_failure_then_rebuild_retry_command_pays_once(self):
        """A player command recovers a saved failed claim without replaying the fight."""
        session = self.start()
        winner = self.defeat_npc(session)
        with patch.object(Trainer, "add_money", side_effect=RuntimeError("wallet unavailable")):
            session.battle.handle_end_of_battle_rewards(winner)
            with self.assertRaises(RuntimeError):
                session.end()
        restored = self.rebuild(session)
        command = CmdBattleRetry()
        command.caller = self.player
        command.func()
        paid = self.wallet()
        self.assertGreater(paid, 0)
        self.assertIsNone(self.player.db.battle_lock)
        self.assertNotIn(restored.battle_id, self.room.db.battles or [])
        command.func()
        self.assertEqual(self.wallet(), paid)

    def test_marker_failure_rolls_back_money_and_retries(self):
        """An outage after wallet save cannot commit money without its marker."""
        session = self.start()
        winner = self.defeat_npc(session)
        original = self.player.attributes.add

        def fail_marker(key, value, *args, **kwargs):
            if kwargs.get("category") == CATEGORY and value.get("claimed"):
                raise RuntimeError("marker unavailable")
            return original(key, value, *args, **kwargs)

        with patch.object(self.player.attributes, "add", fail_marker):
            session.battle.handle_end_of_battle_rewards(winner)
        self.assertEqual(self.wallet(), 0)
        self.assertFalse(session.battle._rewards_granted)
        session.battle.handle_end_of_battle_rewards(winner)
        self.assertGreater(self.wallet(), 0)

    def test_stale_checkpoint_cannot_repeat_faint_effect(self):
        """A committed effect receipt protects even an older room checkpoint."""
        session = self.start()
        old_data = session.data.to_dict()
        old_state = session.state.to_dict()
        session.battle.participants[1].active[0].hp = 0
        session.battle.run_faint()
        awarded = self.exp()
        restored = self.rebuild(session)
        restored.storage.set("data", old_data)
        restored.storage.set("state", old_state)
        battle_handler.unregister(restored)
        for player in self.players:
            player.ndb.battle_instance = None
        stale = BattleSession.restore(self.room, restored.battle_id)
        self.sessions[self.sessions.index(restored)] = stale
        stale.battle.participants[1].active[0].hp = 0
        stale.battle.run_faint()
        self.assertEqual(self.exp(), awarded)

    def test_pending_player_action_and_resources_survive_rebuild(self):
        """A half-declared PvP turn keeps one choice and waits for the other player."""
        session = self.start("pvp")
        active = session.battle.participants[0].active[0]
        active.hp = 10
        active.status = "par"
        active.moves[0].pp = 7
        session.queue_move("Tackle", caller=self.player)
        turn = session.battle.turn_count
        restored = self.rebuild(session)
        active = restored.battle.participants[0].active[0]
        self.assertEqual((active.hp, active.status, active.moves[0].pp), (10, "par", 7))
        self.assertEqual(restored.battle.turn_count, turn)
        self.assertIsNotNone(restored.battle.participants[0].pending_action)
        self.assertIsNone(restored.battle.participants[1].pending_action)
        self.assertFalse(restored.is_turn_ready())

    def declare_double_moves(self, session):
        """Save each active slot's move without advancing the turn."""
        for name, position in session.data.turndata.positions.items():
            pokemon = position.pokemon
            session.state.declare[name] = {
                "move": pokemon.moves[0].name,
                "target": "B1" if name.startswith("A") else "A1",
                "pokemon": pokemon.model_id,
            }

    def test_double_turn_restores_and_executes_every_saved_action_once(self):
        """All four slots execute once, with owned PP and cleared inputs checkpointed."""
        session = self.start("double")
        self.declare_double_moves(session)
        restored = self.rebuild(session)
        self.assertTrue(restored.is_turn_ready())
        expected = {position.pokemon.model_id for position in restored.data.turndata.positions.values()}
        for participant in restored.battle.participants:
            self.assertIsInstance(participant.pending_action, list)
            self.assertEqual(len(participant.pending_action), 2)
        actions = restored.battle.select_actions()
        self.assertEqual({action.pokemon.model_id for action in actions}, expected)
        self.assertEqual(len(actions), 4)
        restored._restore_declarations()
        restored._restore_declarations()
        self.assertEqual([len(part.pending_action) for part in restored.battle.participants], [2, 2])
        before = {mon.model_id: mon.moves[0].pp for part in restored.battle.participants for mon in part.active
                  if getattr(mon.moves[0], "pp", None) is not None}
        turn = restored.battle.turn_count
        restored.battle.rng.seed(0)
        with patch.object(restored.battle, "use_move", wraps=restored.battle.use_move) as moves:
            restored.execute_persistent_turn()
        self.assertEqual(len(moves.call_args_list), 4)
        self.assertEqual({call.args[0].pokemon.model_id for call in moves.call_args_list}, expected)
        self.assertEqual(restored.battle.turn_count, turn + 1)
        for participant in restored.battle.participants:
            for mon in participant.pokemons:
                if mon.model_id in before:
                    self.assertEqual(mon.moves[0].pp, before[mon.model_id] - 1)
        completed = self.rebuild(restored)
        self.assertFalse(completed.state.declare)
        self.assertTrue(all(part.pending_action is None for part in completed.battle.participants))
        for participant in completed.battle.participants:
            for mon in participant.pokemons:
                if mon.model_id in before:
                    self.assertEqual(mon.moves[0].pp, before[mon.model_id] - 1)

    def test_invalid_double_slot_preserves_its_siblings_choice(self):
        """Rejecting the first or last slot cannot erase another legal action."""
        for invalid_slot in ("A1", "A2"):
            with self.subTest(invalid_slot=invalid_slot):
                session = self.start("double")
                self.declare_double_moves(session)
                session.state.declare[invalid_slot]["move"] = "Unavailable Move"
                turn = session.battle.turn_count
                restored = self.rebuild(session)
                valid_slot = "A2" if invalid_slot == "A1" else "A1"
                valid_mon = restored.data.turndata.positions[valid_slot].pokemon
                self.assertNotIn(invalid_slot, restored.state.declare)
                self.assertIn(valid_slot, restored.state.declare)
                self.assertIsNone(restored.data.turndata.positions[invalid_slot].getAction())
                self.assertEqual(restored.battle.turn_count, turn)
                self.assertFalse(restored.is_turn_ready())
                player_actions = restored.battle.participants[0].choose_actions(restored.battle)
                self.assertEqual([action.pokemon.model_id for action in player_actions], [valid_mon.model_id])
                restored.end()

    def test_double_slot_item_and_switch_do_not_overwrite_a_saved_move(self):
        """Mixed choices retain their own actor or reserve alongside the first move."""
        reserve = create_owned_pokemon("Pikachu", self.player.trainer, 5, ivs=[0] * 6, evs=[0] * 6,
                                       nature="Hardy", active_move_names=["Tackle"])
        for declaration, action_type in (({"item": "Potion"}, ActionType.ITEM),
                                         ({"switch": 3}, ActionType.SWITCH)):
            with self.subTest(action_type=action_type):
                session = self.start("double")
                self.declare_double_moves(session)
                session.state.declare["A2"] = declaration
                restored = self.rebuild(session)
                actions = restored.battle.participants[0].choose_actions(restored.battle)
                self.assertEqual([action.action_type for action in actions], [ActionType.MOVE, action_type])
                self.assertIs(actions[0].pokemon, restored.data.turndata.positions["A1"].pokemon)
                if action_type is ActionType.ITEM:
                    self.assertEqual(actions[1].item, "Potion")
                    self.assertIs(actions[1].pokemon, restored.data.turndata.positions["A2"].pokemon)
                else:
                    self.assertEqual(actions[1].pokemon.model_id, "owned:" + str(reserve.pk))
                restored.end()

    def test_faint_marker_failure_rolls_back_all_awards_then_recovers(self):
        """Party EXP/EVs and character TXP share the same claim transaction."""
        session = self.start()
        self.player.db.exp_share = True
        before = self.exp()
        original = self.player.attributes.add

        def fail_marker(key, value, *args, **kwargs):
            if kwargs.get("category") == CATEGORY and value.get("claimed"):
                raise RuntimeError("faint marker unavailable")
            return original(key, value, *args, **kwargs)

        session.battle.participants[1].active[0].hp = 0
        with patch.object(self.player.attributes, "add", fail_marker):
            session.battle.run_faint()
        self.assertEqual(self.exp(), before)
        self.assertFalse(self.player.db.trainer_xp)
        restored = self.rebuild(session)
        restored.retry_battle_rewards()
        awarded = self.exp()
        self.assertGreater(sum(awarded), sum(before))
        self.assertGreater(self.player.db.trainer_xp, 0)
        restored.retry_battle_rewards()
        restored.battle.run_faint()
        self.assertEqual(self.exp(), awarded)

    def test_receipt_write_failure_leaves_faint_retryable(self):
        """A failed intent write must precede the irreversible faint marker."""
        session = self.start()
        target = session.battle.participants[1].active[0]
        target.hp = 0
        before = self.exp()
        original = self.player.attributes.add

        def fail_receipt(key, value, *args, **kwargs):
            if kwargs.get("category") == CATEGORY:
                raise RuntimeError("receipt unavailable")
            return original(key, value, *args, **kwargs)

        with patch.object(self.player.attributes, "add", fail_receipt), self.assertRaises(RuntimeError):
            session.battle.run_faint()
        self.assertFalse(getattr(target, "is_fainted", False))
        self.assertEqual(self.exp(), before)
        session.battle.run_faint()
        self.assertGreater(sum(self.exp()), sum(before))

    def race(self, callbacks):
        """Give each concurrent claimant its own SQL connection and transport."""
        barrier = Barrier(len(callbacks))

        def work(callback):
            close_old_connections()
            try:
                character = ObjectDB.objects.get(pk=self.player.id)
                player = PlayerView(character, Trainer.objects.get(user=character), UserStorage.objects.get(user=character))
                barrier.wait(timeout=10)
                return callback(player)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(callbacks)) as executor:
            return list(executor.map(work, callbacks))

    def test_concurrent_duplicate_claims_pay_once(self):
        """Two independent delivery attempts serialize on the character row."""
        rewards = BattleRewards(uuid4())
        key = rewards.record(self.player, "prize", {"money": 100})
        results = self.race([lambda player: rewards.claim(player, key), lambda player: rewards.claim(player, key)])
        self.assertEqual(results.count(True), 1)
        self.assertEqual(self.wallet(), 100)

    def test_concurrent_distinct_claims_do_not_lose_money(self):
        """Separate battle events cannot overwrite a stale trainer wallet."""
        rewards = BattleRewards(uuid4())
        first = rewards.record(self.player, "first", {"money": 100})
        second = rewards.record(self.player, "second", {"money": 200})
        self.race([lambda player: rewards.claim(player, first), lambda player: rewards.claim(player, second)])
        self.assertEqual(self.wallet(), 300)

    def test_foreign_character_cannot_claim_receipt(self):
        """One account or battle identity never grants access to another character."""
        rewards = BattleRewards(uuid4())
        key = rewards.record(self.player, "prize", {"money": 100})
        with self.assertRaises(ValueError):
            rewards.claim(self.players[1], key)
        self.assertEqual(self.wallet(), 0)

    def test_checkpoint_failure_rolls_back_turn_and_retains_choices(self):
        """A failed final checkpoint cannot consume PP or leave a half-played turn."""
        session = self.start("pvp")
        session.queue_move("Tackle", caller=self.player)
        session.queue_move = lambda *args, **kwargs: None
        for participant in session.battle.participants:
            active = participant.active[0]
            active.moves[0].pp = 35
            target = session.battle.opponent_of(participant)
            participant.pending_action = Action(participant, ActionType.MOVE, target,
                                                  move=BattleMove("Tackle", pp=35), pokemon=active)
        session.state.declare["B1"] = {"move": "tackle", "target": "A1", "trainer": str(self.players[1].id),
                                        "pokemon": session.battle.participants[1].active[0].model_id}
        session._persist_turn_state()
        before = [(p.active[0].hp, p.active[0].moves[0].pp) for p in session.battle.participants]
        turn = session.battle.turn_count
        original = session.storage.set

        def fail_checkpoint(key, value):
            if key == "state":
                raise RuntimeError("checkpoint unavailable")
            return original(key, value)

        with patch.object(session.storage, "set", fail_checkpoint), self.assertRaises(RuntimeError):
            session.execute_persistent_turn()
        self.assertEqual(session.battle.turn_count, turn)
        self.assertEqual([(p.active[0].hp, p.active[0].moves[0].pp) for p in session.battle.participants], before)
        self.assertTrue(all(p.pending_action for p in session.battle.participants))
        session.execute_persistent_turn()
        self.assertEqual(session.battle.turn_count, turn + 1)
        restored = self.rebuild(session)
        self.assertFalse(restored.state.declare)
        self.assertTrue(all(p.pending_action is None for p in restored.battle.participants))

    def test_cleanup_failure_retains_terminal_intent_and_encounter_rows(self):
        """Late cleanup failure rolls back deletes and can finish after rebuild."""
        session = self.start()
        before = EncounterPokemon.objects.count()
        original = session.storage.delete

        def fail_cleanup(part):
            if part == "state":
                raise RuntimeError("cleanup unavailable")
            return original(part)

        with patch.object(session.storage, "delete", fail_cleanup), self.assertRaises(RuntimeError):
            session.end()
        self.assertEqual(EncounterPokemon.objects.count(), before)
        self.assertEqual(self.player.db.battle_lock, session.battle_id)
        restored = self.rebuild(session)
        self.assertTrue(restored.state.ending)
        command = CmdBattleRetry()
        command.caller = self.player
        command.func()
        self.assertIsNone(self.player.db.battle_lock)
        self.assertEqual(EncounterPokemon.objects.count(), before - 2)
        self.assertEqual(self.wallet(), 0)

    def test_duplicate_cleanup_cannot_unlock_a_new_battle(self):
        """An old end callback must not release the player's newer session."""
        old = self.start()
        old.end()
        new = self.start()
        old.end()
        self.assertEqual(self.player.db.battle_lock, new.battle_id)
        self.assertTrue(self.player.db.battle_control)
        self.assertIs(self.player.ndb.battle_instance, new)

    def test_stale_saved_actor_is_discarded_without_advancing_turn(self):
        """A stored move for a replaced active Pokemon cannot run as its reserve."""
        session = self.start("pvp")
        session.queue_move("Tackle", caller=self.player)
        part = session.battle.participants[0]
        part.active = [part.pokemons[1]]
        turn = session.battle.turn_count
        restored = self.rebuild(session)
        self.assertFalse(restored.state.declare)
        self.assertIsNone(restored.battle.participants[0].pending_action)
        self.assertEqual(restored.battle.turn_count, turn)
        self.assertTrue(any("discarded" in str(message) for message in self.player.messages))

    def test_saved_switch_restores_the_requested_legal_reserve(self):
        """A pending switch uses its saved party slot instead of becoming an attack."""
        session = self.start("pvp")
        session.queue_switch(2, caller=self.player)
        restored = self.rebuild(session)
        action = restored.battle.participants[0].pending_action
        self.assertEqual(action.action_type, ActionType.SWITCH)
        self.assertEqual(action.pokemon.name, "Bulbasaur")

    def test_completed_flee_result_survives_rebuild(self):
        """A saved escape cannot be misreported as an Adventure loss after reload."""
        session = self.start("wild")
        participant = session.battle.participants[0]
        participant.flee_attempts = 2
        session.battle._flee_result = {"success": True, "reason": "speed", "participant": participant,
                                      "pokemon": participant.active[0]}
        session.battle.battle_over = True
        restored = self.rebuild(session)
        self.assertTrue(restored.battle._flee_result["success"])
        self.assertTrue(restored.battle.battle_over)
        self.assertEqual(restored.battle.participants[0].flee_attempts, 2)
        self.assertNotIn("participant", restored.state.flee_result)

    def test_participation_history_survives_rebuild(self):
        """Switching and reload keep both legitimate EXP recipients."""
        session = self.start()
        participant = session.battle.participants[0]
        participant.record_participation(participant.pokemons[0])
        participant.active = [participant.pokemons[1]]
        participant.record_participation(participant.pokemons[1])
        restored = self.rebuild(session)
        self.assertEqual(len(restored.battle.participants[0].participating_pokemon), 2)
        before = self.exp()
        restored.battle.participants[1].active[0].hp = 0
        restored.battle.run_faint()
        self.assertTrue(all(after > prior for prior, after in zip(before, self.exp())))

    def test_receipt_plan_is_immutable_and_claimable_without_session(self):
        """A room-independent pending claim retains its first amount through replay."""
        rewards = BattleRewards(uuid4())
        rewards.record(self.player, "prize", {"money": 100})
        rewards.record(self.player, "prize", {"money": 999})
        command = CmdBattleRetry()
        command.caller = self.player
        command.func()
        self.assertEqual(self.wallet(), 100)
        command.func()
        self.assertEqual(self.wallet(), 100)
        self.assertFalse(BattleRewards.pending(self.player))

    def test_active_fusion_receives_faint_award_once_across_rebuild(self):
        """Canonical Fusion placement still receives Pokemon EXP and fighter XP."""
        mon = OwnedPokemon.objects.get(trainer=self.player.trainer, species="Squirtle")
        self.player.storage.reserve_for_fusion(mon)
        self.player.db.fusion_id = str(mon.pk)
        self.player.db.fusion_kind = "permanent"
        self.player.db.fusion_battle_order = "first"
        self.player.db.total_exp = mon.total_exp
        before = mon.total_exp
        session = self.start()
        session.battle.participants[1].active[0].hp = 0
        session.battle.run_faint()
        awarded = OwnedPokemon.objects.values_list("total_exp", flat=True).get(pk=mon.pk)
        self.assertGreater(awarded, before)
        self.assertEqual(self.player.db.total_exp, awarded)
        restored = self.rebuild(session)
        restored.battle.run_faint()
        self.assertEqual(OwnedPokemon.objects.values_list("total_exp", flat=True).get(pk=mon.pk), awarded)
        self.assertEqual(self.player.db.total_exp, awarded)

    def test_capture_rolls_back_with_checkpoint_then_commits_once(self):
        """A failed turn cannot debit a ball or publish a phantom caught Pokemon."""
        session = self.start("wild")
        self.player.trainer.add_item("Master Ball", 1)
        actor, target = session.battle.participants
        actor.pending_action = Action(actor, ActionType.ITEM, target, item="Master Ball", priority=6,
                                      pokemon=actor.active[0])
        session.state.declare["A1"] = {"item": "Master Ball", "target": "B1", "trainer": str(self.player.id),
                                        "pokemon": actor.active[0].model_id}
        session._persist_turn_state()
        before = OwnedPokemon.objects.count()
        original = session.storage.set

        def fail_checkpoint(key, value):
            if key == "state":
                raise RuntimeError("capture checkpoint unavailable")
            return original(key, value)

        with patch.object(session.storage, "set", fail_checkpoint), self.assertRaises(RuntimeError):
            session.execute_persistent_turn()
        self.assertEqual(OwnedPokemon.objects.count(), before)
        self.assertEqual(self.player.trainer.get_item_quantity("Master Ball"), 1)
        self.assertFalse(self.player.ndb.pending_caught_pokemon)
        session.execute_persistent_turn()
        self.assertEqual(OwnedPokemon.objects.count(), before + 1, getattr(session.battle, "_callback_failures", []))
        self.assertEqual(self.player.trainer.get_item_quantity("Master Ball"), 0)
        self.assertEqual(len(self.player.ndb.pending_caught_pokemon), 1)
        restored = self.rebuild(session)
        self.assertTrue(restored.battle.capture_succeeded)
        self.assertFalse(restored.battle.participants[1].pokemons)
        self.assertTrue(restored.battle.participants[1].has_lost)

    def test_damage_source_snapshot_does_not_pickle_live_relationship_managers(self):
        """Live damage sources use roster references rather than ORM object graphs."""
        import pickle

        from evennia.utils.dbserialize import to_pickle

        session = self.start("pvp")
        source = session.battle.participants[0].active[0]
        target = session.battle.participants[1].active[0]
        owned = OwnedPokemon.objects.get(pk=source.model_id.split(":", 1)[1])
        source.live_relationship = owned.activemoveslot_set
        target.tempvals["last_damaged_by"] = {"source": source, "damage": 4, "this_turn": True}
        pickle.dumps(to_pickle(session.data.to_dict()))
        restored = self.rebuild(session)
        target = restored.battle.participants[1].active[0]
        self.assertIs(target.tempvals["last_damaged_by"]["source"], restored.battle.participants[0].active[0])

    def test_switch_command_keeps_canonical_slot_across_checkpoint_restore(self):
        """Party slot six queues the correct compact roster entry and survives restore."""
        first, second = self.player.storage.get_party()
        reserve = create_owned_pokemon("Squirtle", self.player.trainer, 5, ivs=[0] * 6, evs=[0] * 6,
                                       nature="Hardy", active_move_names=["Tackle"])
        placement = PlacementService(self.player.storage)
        box = StorageBox.objects.create(storage=self.player.storage, name="UX storage")
        placement.to_box(first, box)
        placement.to_party(reserve, 6)
        session = self.start("pvp")
        for selection in ("1", "3", "-1", "7"):
            command = CmdBattleSwitch()
            command.caller, command.args = self.player, selection
            command.func()
            self.assertIn("Invalid Pokémon slot", self.player.messages[-1])
            self.assertFalse(session.state.declare)
        self.player.messages.clear()
        command.args = "6"
        command.func()
        self.assertEqual(session.state.declare["A1"]["switch"], 2)
        self.assertEqual(session.battle.participants[0].pending_action.pokemon.model_id, f"owned:{reserve.pk}")
        self.assertEqual(sum("Waiting on" in text for text in self.player.messages), 1)
        self.assertFalse(any("Team A" in text for text in self.player.messages))
        restored = self.rebuild(session)
        self.assertEqual(restored.state.declare["A1"]["switch"], 2)
        self.assertEqual(restored.battle.participants[0].pending_action.pokemon.model_id, f"owned:{reserve.pk}")
        restored.queue_move("tackle", "A1", caller=self.players[1])
        self.assertEqual(restored.battle.participants[0].active[0].model_id, f"owned:{reserve.pk}")
        self.assertEqual(self.player.storage.get_party_slots(), [None, second, None, None, None, reserve])

    def test_item_waiting_feedback_uses_authoritative_opponent_choice(self):
        """A persisted item declaration must not say its own acting Pokemon is missing."""
        session = self.start("pvp")
        self.player.trainer.add_item("Potion", 1)
        self.player.messages.clear()
        session.queue_item("Potion", caller=self.player)
        opponent = session.battle.participants[1].active[0].name
        self.assertEqual(self.player.messages, ["A1 (Squirtle) prepares Potion → A1.", f"Waiting on {opponent}..."])
        self.assertEqual(session._missing_action_positions(), ["B1"])
        self.player.messages.clear()
        saved = dict(session.state.declare)
        session.queue_item("Potion", caller=self.player)
        self.assertEqual(session.state.declare, saved)
        self.assertEqual(len(self.player.messages), 1)
        self.assertIn("already has an action queued", self.player.messages[0])
        self.assertEqual(self.player.trainer.get_item_quantity("Potion"), 1)

    def full_party_fusion_switches(self, order):
        """Exercise the real seven-member roster, saved switch and return switch."""
        fusion = self.player.storage.get_party()[0]
        self.player.storage.reserve_for_fusion(fusion)
        self.player.db.fusion_id = str(fusion.pk)
        self.player.db.fusion_kind = "permanent"
        self.player.db.fusion_species = fusion.species
        self.player.db.fusion_battle_order = order
        for _ in range(5):
            create_owned_pokemon("Bulbasaur", self.player.trainer, 5, ivs=[0] * 6, evs=[0] * 6,
                                 nature="Hardy", active_move_names=["Tackle"])
        slots = self.player.storage.get_party_slots()
        self.assertTrue(all(slots))
        session = self.start("pvp")
        self.assertEqual(len(session.battle.participants[0].pokemons), 7)
        selections = ("6", "fusion", "6", "fusion") if order == "first" else ("fusion", "6", "fusion")
        for selection in selections:
            command = CmdBattleSwitch()
            command.caller, command.args = self.player, selection
            command.func()
            expected = fusion if selection == "fusion" else slots[5]
            expected_id = f"owned:{expected.pk}"
            self.assertEqual(session.battle.participants[0].pending_action.pokemon.model_id, expected_id)
            session = self.rebuild(session)
            self.assertEqual(session.battle.participants[0].pending_action.pokemon.model_id, expected_id)
            session.queue_move("tackle", "A1", caller=self.players[1])
            self.assertEqual(session.battle.participants[0].active[0].model_id, expected_id)
        self.assertEqual(self.player.storage.get_party_slots(), slots)
        fusion.refresh_from_db()
        self.assertEqual(fusion.placement.location_type, "fusion")

    def test_full_party_normally_ordered_fusion_can_switch_in_and_back(self):
        """A normally appended Fusion stays reachable after a party member returns."""
        self.full_party_fusion_switches("normal")

    def test_full_party_first_ordered_fusion_can_switch_out_and_back(self):
        """Leading with the Fusion must not make it unreachable once benched."""
        self.full_party_fusion_switches("first")

    def test_native_form_names_survive_real_attribute_checkpoints(self):
        """Evennia must store native names as text, including repeat rebuilds."""
        from pokemon.battle.terastallization import Terastallization

        forms = (("Ogerpon", "Defiant", ""),
                 ("Ogerpon-Wellspring", "Water Absorb", "Wellspring Mask"),
                 ("Ogerpon-Hearthflame", "Mold Breaker", "Hearthflame Mask"),
                 ("Ogerpon-Cornerstone", "Sturdy", "Cornerstone Mask"),
                 ("Terapagos", "Tera Shift", ""))
        for species, ability, item in forms:
            with self.subTest(species=species):
                OwnedPokemon.objects.filter(trainer=self.player.trainer).delete()
                create_owned_pokemon(species, self.player.trainer, 50, ability=ability,
                                     held_item=item, active_move_names=["Splash"],
                                     nature="Hardy", ivs=[0] * 6, evs=[0] * 6)
                session = self.start("pvp")
                owner = session.battle.participants[0]
                mon = owner.active[0]
                chosen = Terastallization.reserve(session.battle, owner, mon)
                self.assertTrue(Terastallization.activate(session.battle, owner, mon, chosen))
                expected = str(mon.name)
                for _ in range(2):
                    session = self.rebuild(session)
                    mon = session.battle.participants[0].active[0]
                    self.assertIsInstance(mon.name, str)
                    self.assertEqual(mon.name, expected)
                    self.assertEqual(session.battle.tera_used, {"A"})
                # Waiting feedback must also accept a restored native name.
                session.maybe_run_turn(actor=self.player)
                session.end()

    def test_checkpoint_keeps_nicknames_and_plain_names(self):
        """Detaching a native name must not replace ordinary or custom names."""
        session = self.start("pvp")
        owned = OwnedPokemon.objects.get(trainer=self.player.trainer, species="Squirtle")
        owned.nickname = "My Squirtle"
        owned.save(update_fields=["nickname"])
        session.battle.participants[0].active[0].name = "My Squirtle"
        for _ in range(2):
            session = self.rebuild(session)
            self.assertEqual(session.battle.participants[0].active[0].name, "My Squirtle")
            self.assertEqual(session.battle.participants[1].active[0].name, "Squirtle")

    def test_restored_weather_and_terrain_expire_without_restarting(self):
        """Restore handlers without replaying entry effects or resetting timers."""
        cases = (("weather", "SunnyDay", "", 5),
                 ("weather", "RainDance", "Damp Rock", 8),
                 ("terrain", "ElectricTerrain", "", 5),
                 ("terrain", "GrassyTerrain", "Terrain Extender", 8))
        for kind, name, item, duration in cases:
            with self.subTest(kind=kind, name=name):
                session = self.start("pvp")
                battle = session.battle
                source = battle.participants[0].active[0]
                source.item = battle._coerce_item(item)
                self.assertTrue(getattr(battle, "set" + kind.title())(name, source=source))
                key = getattr(battle.field, kind)
                battle.residual()
                self.assertEqual(battle.field.pseudo_weather[key]["duration"], duration - 1)
                session = self.rebuild(session)
                battle = session.battle
                self.assertEqual(battle.field.pseudo_weather[key]["duration"], duration - 1)
                for remaining in range(duration - 2, 0, -1):
                    battle.residual()
                    self.assertEqual(battle.field.pseudo_weather[key]["duration"], remaining)
                battle.residual()
                self.assertIsNone(getattr(battle.field, kind))
                self.assertNotIn(key, battle.field.pseudo_weather)
                session = self.rebuild(session)
                self.assertIsNone(getattr(session.battle.field, kind))
                self.assertFalse(getattr(session.battle.field, kind + "_handler", None))
                session.end()


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from django.db import close_old_connections, connections
        from evennia.commands.cmdset import CmdSet
        from evennia.commands.command import Command
        from evennia.objects.models import ObjectDB

        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle.engine import Action, ActionType, BattleMove, BattleType
        from pokemon.battle.handler import battle_handler
        from pokemon.battle.pokemon_factory import create_battle_pokemon
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon, get_max_hp
        from pokemon.models.core import EncounterPokemon, OwnedPokemon
        from pokemon.models.storage import StorageBox, UserStorage
        from pokemon.models.trainer import NPCPokemonTemplate, NPCTrainer, Trainer
        from pokemon.services.battle_rewards import CATEGORY, BattleRewards
        from pokemon.services.placement import PlacementService
        from pokemon.services.trainer_encounters import generate_static_trainer_encounter
        with patch.object(evennia, "Command", Command), patch.object(evennia, "CmdSet", CmdSet):
            from commands.player.cmd_battle_retry import CmdBattleRetry
            from commands.player.cmd_battle_switch import CmdBattleSwitch

        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BattleRecoveryCases))
        raise SystemExit(not result.wasSuccessful())

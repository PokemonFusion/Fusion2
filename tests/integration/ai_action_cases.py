"""Production PostgreSQL sessions exercising legal AI actions and rebuilds."""

from __future__ import annotations

import random
import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
from ui_cases import PlayerView


class AIActionCases(unittest.TestCase):
    """Keep real storage, sessions, checkpoints, resources and trainer rosters."""

    def setUp(self):
        """Create one player and a three-member NPC team in the isolated schema."""
        room = ObjectDB.objects.create(db_key="AI room " + uuid4().hex[:8])
        self.room = SimpleNamespace(id=room.pk, key=room.key, db=room.db, ndb=room.ndb,
                                    attributes=room.attributes, contents=[])
        character = ObjectDB.objects.create(db_key="AI QA " + uuid4().hex[:8])
        trainer = Trainer.objects.create(user=character, trainer_number=Trainer.objects.count() + 1)
        self.player = PlayerView(character, trainer, UserStorage.objects.create(user=character))
        self.player.location = self.room
        self.room.contents = [self.player]
        for species in ("Squirtle", "Eevee", "Pikachu"):
            create_owned_pokemon(species, trainer, 20, ivs=[0] * 6, evs=[0] * 6,
                                 nature="Hardy", active_move_names=["Tackle", "Water Gun"])
        npc = NPCTrainer.objects.create(name="Legal AI " + uuid4().hex[:8])
        for order, (species, moves) in enumerate((("Vulpix", ["Tackle", "Ember"]),
                                                  ("Squirtle", ["Tackle", "Water Gun"]),
                                                  ("Bulbasaur", ["Tackle", "Vine Whip"])), 1):
            NPCPokemonTemplate.objects.create(npc_trainer=npc, species=species, level=20,
                                              template_key=str(order), sort_order=order,
                                              ivs=[0] * 6, evs=[0] * 6, move_names=moves)
        self.encounter = replace(generate_static_trainer_encounter(npc), ai_profile="trainer_skilled")
        self.session = None
        self.search = patch("pokemon.battle.battleinstance.search_object", self.find)
        self.search.start()

    def tearDown(self):
        """Release only this case's session and transport wrapper."""
        self.search.stop()
        if self.session and self.session.battle_id in (self.room.db.battles or []):
            self.session.end()

    def find(self, query):
        """Resolve the player wrapper while keeping all model operations real."""
        return [self.player] if query == f"#{self.player.id}" else []

    def start(self, *, doubles=False):
        """Start the real trainer encounter with stable seeded battle randomness."""
        self.session = BattleSession(self.player)
        self.session.start_trainer_encounter(replace(self.encounter, battle_format="double" if doubles else "single"))
        self.session.battle.rng = random.Random(2)
        return self.session.battle.participants[1]

    def rebuild(self):
        """Discard runtime references and reconstruct the real stored checkpoint."""
        self.session._sync_active_battle_state()
        self.session._persist_turn_state()
        battle_handler.unregister(self.session)
        self.player.ndb.battle_instance = None
        self.room.ndb.battle_instances = {}
        self.session = BattleSession.restore(self.room, self.session.battle_id)
        self.assertIsNotNone(self.session)
        return self.session.battle.participants[1]

    def test_forced_reserve_survives_rebuild(self):
        """A fainted trainer lead uses the same legal first reserve after rebuild."""
        npc = self.start()
        npc.active[0].hp = 0
        self.session.battle.run_faint()
        reserve = npc.active[0].model_id
        restored = self.rebuild()
        self.assertEqual(restored.active[0].model_id, reserve)
        self.assertEqual(restored.active[0].name, "Squirtle")
        self.assertFalse(restored.has_lost)
        self.assertNotIn(restored.active[0], LegalActions(self.session.battle, restored, restored.active[0]).reserves())

    def test_voluntary_switch_queue_rebuild_execution_and_cooldown(self):
        """Queued switching reaches the actual session and cooldown survives reload."""
        npc = self.start()
        npc.active[0].hp = 1
        with patch.object(self.session.battle.rng, "random", return_value=0):
            self.assertTrue(self.session._auto_queue_ai_actions())
        self.assertIn("switch", self.session.state.declare["B1"])
        chosen = npc.pending_action.pokemon.model_id
        npc = self.rebuild()
        self.assertEqual(npc.pending_action.pokemon.model_id, chosen)
        self.assertEqual(npc.ai_profile, "trainer_skilled")
        self.session.queue_move("Tackle", caller=self.player)
        self.assertFalse(self.session.turn_state.get("error"), self.session.turn_state)
        self.assertEqual(npc.active[0].model_id, chosen)
        npc = self.rebuild()
        self.assertEqual(npc.last_ai_switch_turn, self.session.battle.turn_count)
        npc.active[0].hp = 1
        with patch.object(self.session.battle.rng, "random", return_value=0):
            self.assertEqual(_select_ai_action(npc, npc.active[0], self.session.battle).action_type, ActionType.MOVE)

    def test_disabled_saved_preference_uses_legal_move_once(self):
        """A disabled checkpoint choice falls back before order and spends only legal PP."""
        npc = self.start()
        user = npc.active[0]
        chosen = next(action for action in LegalActions(self.session.battle, npc, user).moves() if action.move.name == "Ember")
        npc.pending_action = chosen
        user.volatiles["disable"] = chosen.move
        self.session.data.turndata.positions["B1"].declareAttack("A1", "Ember")
        self.session.state.declare["B1"] = {"move": "Ember", "target": "A1", "pokemon": user.model_id}
        npc = self.rebuild()
        before = {move.name: getattr(move, "pp", get_pp(MOVEDEX[_normalize_key(move.name)])) for move in npc.active[0].moves}
        turn = self.session.battle.turn_count
        self.session.queue_move("Tackle", caller=self.player)
        self.assertFalse(self.session.turn_state.get("error"), self.session.turn_state)
        self.assertEqual(self.session.battle.turn_count, turn + 1)
        npc = self.rebuild()
        after = {move.name: getattr(move, "pp", get_pp(MOVEDEX[_normalize_key(move.name)])) for move in npc.active[0].moves}
        self.assertEqual(after["Ember"], before["Ember"])
        self.assertEqual(after["Tackle"], before["Tackle"] - 1)

    def test_trap_and_choice_controls_survive_checkpoint(self):
        """Restored legality retains choice locks, move references and rooted state."""
        npc = self.start()
        user = npc.active[0]
        user.item = "Choice Band"
        user.choice_locked_move = "ember"
        user.volatiles["ingrain"] = True
        user.volatiles["disable"] = BattleMove("Tackle", onHit=lambda *args: True)
        npc = self.rebuild()
        legal = LegalActions(self.session.battle, npc, npc.active[0])
        self.assertFalse(legal.switches())
        self.assertEqual({action.move.name for action in legal.moves()}, {"Ember"})
        npc.active[0].hp = 0
        self.assertTrue(legal.reserves(slot=0, forced=True))

    def test_exhausted_moves_use_struggle_and_advance(self):
        """No-PP NPCs execute the emergency move instead of stalling a ready turn."""
        npc = self.start()
        for move in npc.active[0].moves:
            move.pp = 0
        turn = self.session.battle.turn_count
        player_mon = self.session.battle.participants[0].active[0]
        before_hp = player_mon.hp
        self.session.queue_move("Tackle", caller=self.player)
        self.assertFalse(self.session.turn_state.get("error"), self.session.turn_state)
        self.assertEqual(self.session.battle.turn_count, turn + 1)
        self.assertLess(player_mon.hp, before_hp)
        self.assertTrue(all(move.pp == 0 for move in npc.active[0].moves))
        stored = OwnedPokemon.objects.get(pk=player_mon.model_id.split(":", 1)[1])
        self.assertEqual(stored.current_hp, player_mon.hp)

    def test_two_ai_slots_retain_actions_and_distinct_reserves(self):
        """A double NPC queues two actions without overwriting or double-booking."""
        npc = self.start(doubles=True)
        for pokemon in npc.active:
            pokemon.hp = 1
        with patch.object(self.session.battle.rng, "random", return_value=0):
            self.assertTrue(self.session._auto_queue_ai_actions())
        self.assertEqual(len(npc.pending_action), 2)
        incoming = [action.pokemon.model_id for action in npc.pending_action if action.action_type is ActionType.SWITCH]
        self.assertEqual(len(incoming), 1)
        self.assertEqual(len(incoming), len(set(incoming)))
        self.assertIn("B1", self.session.state.declare)
        self.assertIn("B2", self.session.state.declare)
        npc = self.rebuild()
        self.assertEqual(len(npc.pending_action), 2)
        self.assertEqual(len({action.switch_from or action.pokemon for action in npc.pending_action}), 2)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        from evennia.objects.models import ObjectDB

        from pokemon.battle._shared import _normalize_key, get_pp
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle.engine import ActionType, BattleMove, _select_ai_action
        from pokemon.battle.handler import battle_handler
        from pokemon.battle.legal_actions import LegalActions
        from pokemon.dex import MOVEDEX
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.storage import UserStorage
        from pokemon.models.trainer import NPCPokemonTemplate, NPCTrainer, Trainer
        from pokemon.services.trainer_encounters import generate_static_trainer_encounter

        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AIActionCases))
        raise SystemExit(not result.wasSuccessful())

"""Doubles AI choices through actual gym encounters and PostgreSQL checkpoints."""

from __future__ import annotations

import random
import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
from ui_cases import PlayerView


class AIScoringCases(unittest.TestCase):
    """Exercise selection, execution, resources, fainting and rebuilds together."""

    def setUp(self):
        """Create a real gym profile and two fast normal-player active Pokémon."""
        room = ObjectDB.objects.create(db_key="Scoring room " + uuid4().hex[:8])
        self.room = SimpleNamespace(id=room.pk, key=room.key, db=room.db, ndb=room.ndb,
                                    attributes=room.attributes, contents=[])
        character = ObjectDB.objects.create(db_key="Scoring QA " + uuid4().hex[:8])
        trainer = Trainer.objects.create(user=character, trainer_number=Trainer.objects.count() + 1)
        self.player = PlayerView(character, trainer, UserStorage.objects.create(user=character))
        self.player.location = self.room
        self.room.contents = [self.player]
        self.owned = [create_owned_pokemon(species, trainer, 50, ivs=[0] * 6, evs=[0] * 6,
                                          nature="Hardy", active_move_names=["Tackle", "Water Gun"])
                      for species in ("Jolteon", "Electrode", "Eevee")]
        npc = NPCTrainer.objects.create(name="Speed Gym " + uuid4().hex[:8])
        self.templates = [NPCPokemonTemplate.objects.create(
            npc_trainer=npc, species=species, level=50, template_key=str(index), sort_order=index,
            ivs=[0] * 6, evs=[0] * 6, nature="Hardy", move_names=moves)
            for index, (species, moves) in enumerate((("Slowbro", ["Trick Room", "Water Gun"]),
                                                       ("Slowking", ["Trick Room", "Water Gun"]),
                                                       ("Snorlax", ["Tackle"])), 1)]
        badge = GymBadge.objects.create(name="Scoring Badge " + uuid4().hex[:8], region="Disposable QA")
        self.profile = GymLeaderProfile.objects.create(npc_trainer=npc, badge=badge, league_key="qa",
                                                       gym_key=uuid4().hex[:8], badge_key=uuid4().hex[:8])
        self.session = None
        self.search = patch("pokemon.battle.battleinstance.search_object", self.find)
        self.search.start()

    def tearDown(self):
        """Release only this schema's test session and captured player transport."""
        if self.session and self.session.battle_id in (self.room.db.battles or []):
            self.session.end()
        self.search.stop()

    def find(self, query):
        """Keep all models real while resolving the ordinary-player transport."""
        return [self.player] if str(query).lstrip("#") == str(self.player.id) else []

    def configure(self, index, species, moves):
        """Change only a disposable gym template before encounter generation."""
        row = self.templates[index]
        row.species, row.move_names = species, moves
        row.save(update_fields=["species", "move_names"])

    def start(self):
        """Use production gym resolution and the shared trainer-session adapter."""
        encounter = replace(generate_gym_leader_encounter(self.profile, player=self.player),
                            ai_profile="gym_trick_room", battle_format="double")
        self.session = BattleSession(self.player)
        self.session.start_trainer_encounter(encounter)
        self.session.battle.rng = random.Random(5)
        return self.session.battle.participants[1]

    def rebuild(self):
        """Restore the saved session after dropping every runtime transport reference."""
        self.session._sync_active_battle_state()
        self.session._persist_turn_state()
        battle_handler.unregister(self.session)
        self.player.ndb.battle_instance = None
        self.room.ndb.battle_instances = {}
        self.session = BattleSession.restore(self.room, self.session.battle_id)
        self.assertIsNotNone(self.session)
        return self.session.battle.participants[1]

    def advance(self, target="B1"):
        """Submit independent legal player actions and execute one persisted turn."""
        turn = self.session.battle.turn_count
        positions = list(self.session.choices_for(self.player).positions())
        for name in positions:
            self.session.queue_move("Tackle", target, caller=self.player, actor=name)
        self.assertFalse(self.session.turn_state.get("error"), self.session.turn_state)
        self.assertEqual(self.session.battle.turn_count, turn + 1)

    def test_profile_two_actions_and_room_survive_execution_and_rebuild(self):
        """One room declaration, both actors and the configured profile survive reload."""
        npc = self.start()
        self.assertTrue(self.session._auto_queue_ai_actions())
        self.assertEqual(len(npc.pending_action), 2)
        self.assertEqual([action.move.name for action in npc.pending_action].count("Trick Room"), 1)
        npc = self.rebuild()
        self.assertEqual(npc.ai_profile, "gym_trick_room")
        self.assertEqual(len(npc.pending_action), 2)
        self.advance()
        self.assertTrue(self.session.battle.field.get_pseudo_weather("trickroom"))
        npc = self.rebuild()
        self.assertEqual(npc.ai_profile, "gym_trick_room")
        self.assertTrue(self.session.battle.field.get_pseudo_weather("trickroom"))
        self.assertTrue(self.session._auto_queue_ai_actions())
        self.assertTrue(all(action.move.name != "Trick Room" for action in npc.pending_action))
        slow = next(action for action in LegalActions(self.session.battle, npc, npc.active[0]).moves()
                    if action.move.name == "Water Gun")
        human = self.session.battle.participants[0]
        fast = next(action for action in LegalActions(self.session.battle, human, human.active[0]).moves()
                    if action.move.name == "Tackle")
        self.assertIs(self.session.battle.order_actions([fast, slow])[0].pokemon, npc.active[0])

    def test_room_duration_is_preserved_and_expires_after_rebuild(self):
        """A restored field retains its remaining duration rather than lasting forever."""
        self.start()
        self.advance()
        field = self.session.battle.field
        before = field.get_pseudo_weather("trickroom")
        self.assertEqual(before["duration"], 4)
        self.rebuild()
        restored = self.session.battle.field.get_pseudo_weather("trickroom")
        self.assertEqual(restored["duration"], before["duration"])
        self.assertIs(restored["target"], self.session.battle.field)
        self.assertIs(restored["source"], self.session.battle.participants[1].active[0])
        for expected in (3, 2, 1):
            self.session.battle.residual()
            self.assertEqual(self.session.battle.field.get_pseudo_weather("trickroom")["duration"], expected)
        self.session.battle.residual()
        self.assertFalse(self.session.battle.field.get_pseudo_weather("trickroom"))

    def test_spread_choice_hits_both_foes_and_spares_flying_ally(self):
        """Earthquake's scored set matches both authoritative foe HP results."""
        self.configure(0, "Golem", ["Earthquake", "Rock Slide"])
        self.configure(1, "Pidgeot", ["Tackle"])
        npc = self.start()
        ally_hp = npc.active[1].hp
        self.session._auto_queue_ai_actions()
        self.assertEqual(npc.pending_action[0].move.name, "Earthquake")
        trace = self.session.battle.ai_debug_traces[-2].to_dict()
        spread = next(score for score in trace["scores"] if score["action"].lower() == "earthquake")
        self.assertIn("A1", spread["target"])
        self.assertIn("A2", spread["target"])
        self.assertIn("B2", spread["target"])
        self.advance()
        for owned in self.owned[:2]:
            owned.refresh_from_db()
            self.assertLess(owned.current_hp, owned.get_max_hp())
        self.assertEqual(npc.active[1].hp, ally_hp)

    def test_recovery_selects_self_and_spends_one_pp_after_rebuild(self):
        """An injured actor restores its own HP, retaining selection and PP identity."""
        self.configure(0, "Mew", ["Recover", "Tackle"])
        self.configure(1, "Snorlax", ["Tackle"])
        npc = self.start()
        npc.active[0].hp = npc.active[0].max_hp // 5
        self.session._auto_queue_ai_actions()
        action = npc.pending_action[0]
        self.assertEqual(action.move.name, "Recover")
        self.assertIs(action.target_pokemon, npc.active[0])
        npc = self.rebuild()
        before = npc.active[0].hp
        self.advance(target="B2")
        npc = self.rebuild()
        self.assertGreater(npc.active[0].hp, before)
        move = next(move for move in npc.active[0].moves if move.name == "Recover")
        self.assertEqual(move.pp, get_pp(MOVEDEX[_normalize_key("Recover")]) - 1)

    def test_ally_pollen_puff_heals_without_a_friendly_damage_hit(self):
        """The chosen ally branch executes as healing through a real engine turn."""
        self.configure(0, "Butterfree", ["Pollen Puff", "Tackle"])
        self.configure(1, "Snorlax", ["Tackle"])
        npc = self.start()
        ally = npc.active[1]
        ally.hp = ally.max_hp // 10
        before = ally.hp
        self.session._auto_queue_ai_actions()
        action = npc.pending_action[0]
        self.assertEqual(action.move.name, "Pollen Puff")
        self.assertIs(action.target_pokemon, ally)
        npc = self.rebuild()
        self.assertEqual(npc.pending_action[0].target_slot, 1)
        self.advance()
        self.assertEqual(npc.active[1].hp, min(ally.max_hp, before + ally.max_hp // 2))
        move = next(move for move in npc.active[0].moves if move.name == "Pollen Puff")
        self.assertEqual(move.pp, get_pp(MOVEDEX[_normalize_key("Pollen Puff")]) - 1)

    def test_protect_uses_visible_residual_and_persists_stall_state(self):
        """Protect prevents the selected hits while residual damage advances."""
        self.configure(0, "Eevee", ["Protect", "Tackle"])
        self.configure(1, "Slowbro", ["Water Gun"])
        npc = self.start()
        npc.active[0].hp = npc.active[0].max_hp // 5
        before = npc.active[0].hp
        for pokemon in self.session.battle.participants[0].active:
            pokemon.status = "tox"
        self.session._auto_queue_ai_actions()
        self.assertEqual(npc.pending_action[0].move.name, "Protect")
        self.advance()
        self.assertEqual(npc.active[0].hp, before)
        npc = self.rebuild()
        self.assertIn("stall", npc.active[0].volatiles)
        npc.active[0].volatiles["stall"]["counter"] = 8
        selected = _select_ai_action(npc, npc.active[0], self.session.battle)
        self.assertTrue(selected.move is None or selected.move.name != "Protect")

    def test_fainted_target_and_empty_slot_recover_pending_actions(self):
        """A vanished target is refreshed to the surviving logical A2 on reload."""
        self.configure(0, "Squirtle", ["Water Gun"])
        self.configure(1, "Squirtle", ["Water Gun"])
        self.start()
        human = self.session.battle.participants[0]
        human.active[0].hp = 1
        self.session._auto_queue_ai_actions()
        human.active[0].hp = human.pokemons[2].hp = 0
        self.session.battle.run_faint()
        self.session._sync_active_battle_state()
        npc = self.rebuild()
        self.assertTrue(all(action.target_slot == 1 for action in npc.pending_action))
        self.assertTrue(all(self.session.state.declare[name]["target"] == "A2" for name in ("B1", "B2")))
        npc = self.rebuild()
        self.assertTrue(all(action.target_slot == 1 for action in npc.pending_action))
        before = self.session.data.turndata.positions["A2"].pokemon.hp
        self.advance()
        self.assertLess(self.session.data.turndata.positions["A2"].pokemon.hp, before)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        from evennia.objects.models import ObjectDB

        from pokemon.battle._shared import _normalize_key, get_pp
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle.engine import _select_ai_action
        from pokemon.battle.handler import battle_handler
        from pokemon.battle.legal_actions import LegalActions
        from pokemon.dex import MOVEDEX
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.models.storage import UserStorage
        from pokemon.models.trainer import GymBadge, GymLeaderProfile, NPCPokemonTemplate, NPCTrainer, Trainer
        from pokemon.services.gym_leaders import generate_gym_leader_encounter

        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AIScoringCases))
        raise SystemExit(not result.wasSuccessful())

"""Real PostgreSQL battle progression regressions in a disposable schema.

Run with an explicit PF2_TEST_POSTGRES_DSN. No game rows, migrations, or
running Evennia process are touched; IsolatedPostgres guards every connection.
"""

from __future__ import annotations

import math
import unittest
from types import SimpleNamespace
from uuid import uuid4

from isolated_postgres import IsolatedPostgres


class ProgressionCases(unittest.TestCase):
    """Use production models and battle reward/cleanup/healing functions."""

    def setUp(self):
        """Create a trainer and canonical party wholly inside the test schema."""
        self.character = ObjectDB.objects.create(db_key="progression-" + uuid4().hex)
        self.trainer = Trainer.objects.create(
            user=self.character, trainer_number=Trainer.objects.count() + 1,
        )
        self.storage = UserStorage.objects.create(user=self.character)
        self.character.db.exp_share = False
        self.player = SimpleNamespace(
            key=self.character.key, storage=self.storage, trainer=self.trainer,
            db=self.character.db, msg=lambda message: None,
        )

    def pokemon(self, species="Squirtle", *, active_move_names=None):
        """Create a real owned Pokemon, generated moves, and party placement."""
        return create_owned_pokemon(
            species, self.trainer, 5, nature="Hardy", gender="M",
            ivs=[12, 8, 20, 14, 10, 16], evs=[0, 0, 0, 0, 0, 0],
            active_move_names=active_move_names or ["Tackle"],
        )

    def win(self, owned, *, remaining_hp=3, target_level=5):
        """Run the real faint-reward path, then the real player HP sync."""
        battle_mon = build_battle_pokemon_from_model(owned)
        battle_mon.hp = remaining_hp
        target = Pokemon("Pidgey", level=target_level, hp=0, max_hp=20)
        player_part = BattleParticipant("Player", [battle_mon], player=self.player)
        opponent = BattleParticipant("Opponent", [target], is_ai=True)
        player_part.active = [battle_mon]
        opponent.active = [target]
        battle = Battle(BattleType.WILD, [player_part, opponent])
        battle.run_faint()
        BattleSession._sync_player_pokemon_state(SimpleNamespace(battle=battle))
        return battle_mon

    def stored(self, owned):
        """Read fresh SQL values, avoiding Evennia's shared model cache."""
        return OwnedPokemon.objects.filter(pk=owned.pk).values().get()

    def assert_spent_pp_persists(self, species, stored_name, display_name, uses, *, fusion=False):
        """Spend PP through real moves, then check SQL, snapshots and healing."""
        owned = self.pokemon(species, active_move_names=[stored_name])
        if fusion:
            self.storage.reserve_for_fusion(owned)
            self.player.db.fusion_id = str(owned.pk)
            self.player.db.fusion_kind = "permanent"
            owned = get_battle_party_with_fusion(self.player)[0]
        active = build_battle_pokemon_from_model(owned)
        initial_pp = owned.activemoveslot_set.values_list("current_pp", flat=True).get()
        # Battle snapshots can already carry a PP value when restored.
        active.moves[0].pp = initial_pp
        target_model = create_owned_pokemon(
            "Snorlax", self.trainer, 100, nature="Hardy", active_move_names=["Tackle"],
        )
        target = build_battle_pokemon_from_model(target_model)
        for index in range(uses):
            if index:
                active = Pokemon.from_dict(active.to_dict())
            player = BattleParticipant("Player", [active], player=self.player)
            opponent = BattleParticipant("Opponent", [target], is_ai=True)
            player.active = [active]
            opponent.active = [target]
            battle = Battle(BattleType.WILD, [player, opponent])
            move = BattleMove(display_name)
            battle.use_move(Action(player, ActionType.MOVE, opponent, move, pokemon=active))
            self.assertEqual(move.pp, initial_pp - index - 1)
            self.assertEqual(
                owned.activemoveslot_set.values_list("current_pp", flat=True).get(),
                initial_pp - index - 1,
            )
        self.assertLess(target.hp, target.max_hp)
        BattleSession._sync_player_pokemon_state(SimpleNamespace(battle=battle))

        expected = initial_pp - uses
        self.assertEqual(owned.activemoveslot_set.values_list("current_pp", flat=True).get(), expected)
        self.assertEqual(active.to_dict()["moves"][0]["pp"], expected)
        self.assertEqual(Pokemon.from_dict(active.to_dict()).moves[0].pp, expected)
        next_battle = build_battle_pokemon_from_model(owned)
        self.assertEqual(next_battle.to_dict()["moves"][0]["pp"], expected)
        owned.heal()
        self.assertEqual(owned.activemoveslot_set.values_list("current_pp", flat=True).get(), initial_pp)

    def test_water_gun_pp_survives_next_battle_and_heals(self):
        """The four Water Gun uses from live testing must spend four saved PP."""
        self.assert_spent_pp_persists("Squirtle", "Watergun", "Water Gun", 4)

    def test_reserved_fusion_dragon_rage_pp_persists_and_heals(self):
        """A reserved Fusion's move slot uses the same durable PP path."""
        self.assert_spent_pp_persists("Garchomp", "Dragonrage", "Dragon Rage", 3, fusion=True)

    def test_exhausted_stored_move_cannot_attack(self):
        """A fresh battle must respect zero PP in the saved slot."""
        owned = self.pokemon(active_move_names=["Watergun"])
        owned.activemoveslot_set.update(current_pp=0)
        active = build_battle_pokemon_from_model(owned)
        target = build_battle_pokemon_from_model(self.pokemon("Pidgey"))
        player = BattleParticipant("Player", [active], player=self.player)
        opponent = BattleParticipant("Opponent", [target], is_ai=True)
        player.active = [active]
        opponent.active = [target]
        battle = Battle(BattleType.WILD, [player, opponent])
        move = BattleMove("Water Gun")

        battle.use_move(Action(player, ActionType.MOVE, opponent, move, pokemon=active))

        self.assertEqual(move.pp, 0)
        self.assertEqual(target.hp, target.max_hp)
        self.assertEqual(owned.activemoveslot_set.values_list("current_pp", flat=True).get(), 0)

    def test_win_persists_exp_evs_and_remaining_hp(self):
        """A win must survive fresh reads and leave legal ArrayField data."""
        owned = self.pokemon()
        initial = self.stored(owned)
        self.win(owned)
        stored = self.stored(owned)
        gain = math.floor(GAIN_INFO["Pidgey"]["exp"] * 5 / 7)
        self.assertEqual(stored["total_exp"], initial["total_exp"] + gain)
        self.assertEqual(stored["evs"], [0, 0, 0, 0, 0, 1])
        self.assertEqual(stored["current_hp"], 3)
        self.assertIsInstance(owned.evs, list)

    def test_heal_after_win_persists_hp_and_pp(self):
        """The live post-win healing traceback must not recur on PostgreSQL."""
        owned = self.pokemon()
        self.win(owned)
        owned.activemoveslot_set.update(current_pp=0)
        owned.heal()
        self.assertEqual(self.stored(owned)["current_hp"], get_max_hp(owned))
        self.assertTrue(all(pp > 0 for pp in owned.activemoveslot_set.values_list("current_pp", flat=True)))

    def test_level_up_and_new_max_hp_survive_fresh_reads(self):
        """Enough EXP persists the new level, and the next battle uses its HP."""
        owned = self.pokemon()
        initial = owned.total_exp
        self.win(owned, target_level=20)
        gain = math.floor(GAIN_INFO["Pidgey"]["exp"] * 20 / 7)
        stored = self.stored(owned)
        self.assertEqual(stored["total_exp"], initial + gain)
        self.assertGreater(stored["level"], 5)
        next_battle = build_battle_pokemon_from_model(owned)
        self.assertEqual(next_battle.level, stored["level"])
        self.assertEqual(next_battle.max_hp, get_max_hp(owned))

    def test_hp_sync_does_not_save_unrelated_fields(self):
        """Cleanup writes HP/status without relying on a full-save fallback."""
        owned = self.pokemon()
        # An unrelated in-memory field must not be written by battle cleanup.
        owned.nickname = "unsaved-change"
        battle_mon = build_battle_pokemon_from_model(owned)
        battle_mon.hp = 2
        battle = SimpleNamespace(participants=[SimpleNamespace(player=self.player, pokemons=[battle_mon])])
        BattleSession._sync_player_pokemon_state(SimpleNamespace(battle=battle))
        stored = self.stored(owned)
        self.assertEqual(stored["current_hp"], 2)
        self.assertEqual(stored["nickname"], "")

    def test_next_battle_keeps_calculated_max_hp(self):
        """Damage persists without turning remaining HP into a new maximum."""
        owned = self.pokemon()
        owned.current_hp = 3
        owned.save(update_fields=["current_hp"])
        battle_mon = build_battle_pokemon_from_model(owned)
        self.assertEqual(battle_mon.hp, 3)
        self.assertEqual(battle_mon.max_hp, get_max_hp(owned))

    def test_fainted_pokemon_keeps_zero_hp(self):
        """A loss persists a faint instead of restoring the previous party HP."""
        owned = self.pokemon()
        battle_mon = build_battle_pokemon_from_model(owned)
        battle_mon.hp = 0
        battle = SimpleNamespace(participants=[SimpleNamespace(player=self.player, pokemons=[battle_mon])])
        BattleSession._sync_player_pokemon_state(SimpleNamespace(battle=battle))
        self.assertEqual(self.stored(owned)["current_hp"], 0)
        self.assertEqual(build_battle_pokemon_from_model(owned).hp, 0)

    def test_reserved_fusion_receives_exp_and_hp_sync(self):
        """An active permanent form progresses even outside normal party slots."""
        owned = self.pokemon("Pikachu")
        self.storage.reserve_for_fusion(owned)
        self.player.db.fusion_id = str(owned.pk)
        self.player.db.fusion_kind = "permanent"
        self.player.db.total_exp = owned.total_exp
        initial = owned.total_exp
        form = get_battle_party_with_fusion(self.player)[0]
        self.win(form)
        gain = math.floor(GAIN_INFO["Pidgey"]["exp"] * 5 / 7)
        self.assertEqual(self.stored(owned)["total_exp"], initial + gain)
        self.assertEqual(self.player.db.total_exp, initial + gain)
        attribute = self.character.attributes.get("total_exp", return_obj=True)
        self.assertEqual(
            Attribute.objects.filter(pk=attribute.pk).values_list("db_value", flat=True).get(),
            initial + gain,
        )
        self.assertEqual(self.stored(owned)["current_hp"], 3)

    def test_switched_participant_receives_exp_not_first_slot(self):
        """A typed owned ref identifies the actual participating party member."""
        first = self.pokemon()
        second = self.pokemon("Rattata")
        first_exp = first.total_exp
        second_exp = second.total_exp
        self.win(second)
        gain = math.floor(GAIN_INFO["Pidgey"]["exp"] * 5 / 7)
        self.assertEqual(self.stored(first)["total_exp"], first_exp)
        self.assertEqual(self.stored(second)["total_exp"], second_exp + gain)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        from evennia.objects.models import ObjectDB
        from evennia.typeclasses.attributes import Attribute

        from pokemon.battle.battledata import Pokemon
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle.engine import Action, ActionType, Battle, BattleMove, BattleParticipant, BattleType
        from pokemon.dex.exp_ev_yields import GAIN_INFO
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon, get_max_hp
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.storage import UserStorage
        from pokemon.models.trainer import Trainer
        from utils.fusion import get_battle_party_with_fusion
        from utils.pokemon_utils import build_battle_pokemon_from_model

        unittest.main(verbosity=2)

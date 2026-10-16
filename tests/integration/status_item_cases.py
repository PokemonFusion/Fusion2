"""Item routing and durable conditions using production PostgreSQL models.

Run with an explicit PF2_TEST_POSTGRES_DSN. All fixture writes are guarded to
one disposable schema; no migrations or live game rows are touched.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from uuid import uuid4

from isolated_postgres import IsolatedPostgres


class StatusItemCases(unittest.TestCase):
    """Check gameplay effects across SQL reads, cleanup and new battles."""

    def setUp(self):
        """Create a player, canonical party member and injured opponent."""
        self.character = ObjectDB.objects.create(db_key="status-item-" + uuid4().hex)
        self.trainer = Trainer.objects.create(user=self.character, trainer_number=Trainer.objects.count() + 1)
        self.storage = UserStorage.objects.create(user=self.character)
        self.player = SimpleNamespace(
            key=self.character.key, trainer=self.trainer, storage=self.storage,
            db=self.character.db, ndb=SimpleNamespace(), msg=lambda text: None,
        )
        self.owned = create_owned_pokemon(
            "Squirtle", self.trainer, 5, nature="Hardy", ivs=[0] * 6, evs=[0] * 6,
            active_move_names=["Watergun"],
        )
        self.active = build_battle_pokemon_from_model(self.owned)
        self.actor = BattleParticipant("Player", [self.active], player=self.player)
        self.foe = BattleParticipant("Foe", [Pokemon("Rattata", level=5, hp=10, max_hp=20)])
        self.actor.active = [self.active]
        self.foe.active = [self.foe.pokemons[0]]
        self.battle = Battle(BattleType.WILD, [self.actor, self.foe])

    def sync(self):
        """Use production cleanup, then refresh the owned model from SQL."""
        BattleSession._sync_player_pokemon_state(SimpleNamespace(battle=self.battle))
        self.owned.refresh_from_db()

    def item(self, item, target=None):
        """Execute the real item path, including malformed old opponent targets."""
        self.battle.execute_item(Action(self.actor, ActionType.ITEM, target, item=item))

    def test_potion_with_old_opponent_target_heals_only_own_pokemon(self):
        """A valid but incorrect old target must not heal the enemy."""
        self.trainer.add_item("potion", 2)
        self.active.hp = 3
        self.item("potion", self.foe)
        self.sync()
        self.assertEqual(self.owned.current_hp, self.active.max_hp)
        self.assertEqual(self.foe.active[0].hp, 10)
        self.assertEqual(self.trainer.get_item_quantity("potion"), 1)

    def test_potion_at_full_hp_does_not_heal_enemy_or_spend_item(self):
        """An injured opponent cannot make the player's medicine usable."""
        self.trainer.add_item("potion", 2)
        self.item("potion", self.foe)
        self.assertEqual(self.trainer.get_item_quantity("potion"), 2)
        self.assertEqual(self.foe.active[0].hp, 10)

    def test_all_major_conditions_survive_cleanup_and_next_battle(self):
        """Conditions and remaining sleep turns survive genuine SQL reloads."""
        for status in ("psn", "brn", "par", "tox", "slp", "frz"):
            with self.subTest(status=status):
                self.active.setStatus(0)
                self.assertTrue(self.active.setStatus(status))
                if status == "slp":
                    self.active.tempvals["sleep_turns"] = 1
                self.sync()
                self.assertEqual(self.owned.status, status)
                restored = build_battle_pokemon_from_model(self.owned)
                self.assertEqual(restored.status, status)
                if status == "slp":
                    self.assertEqual(restored.tempvals["sleep_turns"], 1)

    def test_sleep_progress_and_waking_survive_repeated_battles(self):
        """Rebuilding never rerolls sleep or loses a pending wake-up at zero."""
        self.active.setStatus("slp", effect="move:rest")
        handler = CONDITION_HANDLERS["slp"]
        for remaining in (1, 0):
            self.assertFalse(handler.onBeforeMove(self.active, battle=self.battle))
            self.sync()
            self.assertEqual(self.owned.sleep_turns, remaining)
            self.active = build_battle_pokemon_from_model(self.owned)
            self.actor.pokemons = self.actor.active = [self.active]
        self.assertTrue(handler.onBeforeMove(self.active, battle=self.battle))
        self.sync()
        self.assertEqual(self.owned.status, "")
        self.assertIsNone(self.owned.sleep_turns)

    def test_cure_stays_cured_after_cleanup(self):
        """An Antidote cures the player's saved poison and spends once."""
        self.trainer.add_item("antidote", 2)
        self.active.setStatus("psn")
        self.sync()
        self.item("antidote", self.foe)
        self.sync()
        self.assertEqual(self.owned.status, "")
        self.assertFalse(build_battle_pokemon_from_model(self.owned).status)
        self.assertEqual(self.trainer.get_item_quantity("antidote"), 1)

    def test_heal_and_full_heal_builder_clear_status_and_sleep(self):
        """Healing clears saved conditions; a preview heal leaves SQL alone."""
        self.active.hp = 3
        self.active.setStatus("slp", effect="move:rest")
        self.sync()
        healed = build_battle_pokemon_from_model(self.owned, full_heal=True)
        self.assertFalse(healed.status)
        self.assertNotIn("sleep_turns", healed.tempvals)
        self.assertEqual(self.owned.status, "slp")
        self.owned.heal()
        self.owned.refresh_from_db()
        self.assertEqual(self.owned.status, "")
        self.assertIsNone(self.owned.sleep_turns)
        self.assertEqual(self.owned.current_hp, get_max_hp(self.owned))

    def test_reserved_fusion_status_survives_cleanup_and_heal(self):
        """A reserved Fusion uses the same durable status path as the party."""
        self.storage.reserve_for_fusion(self.owned)
        self.player.db.fusion_id = str(self.owned.pk)
        self.player.db.fusion_kind = "permanent"
        self.active.setStatus("brn")
        self.sync()
        form = get_battle_party_with_fusion(self.player)[0]
        self.assertEqual(build_battle_pokemon_from_model(form).status, "brn")
        form.heal()
        self.owned.refresh_from_db()
        self.assertEqual(self.owned.status, "")

    def test_box_roundtrip_keeps_status(self):
        """Deposit/withdraw cannot cure a persistent condition."""
        self.active.setStatus("par")
        self.sync()
        box = StorageBox.objects.create(storage=self.storage, name="Status Box")
        service = PlacementService(self.storage)
        service.to_box(self.owned, box)
        service.to_party(self.owned, 1)
        self.owned.refresh_from_db()
        self.assertEqual(build_battle_pokemon_from_model(self.owned).status, "par")

    def test_capture_retains_live_status_and_sleep_progress(self):
        """Capture preserves the current condition, rather than stale encounter state."""
        encounter = create_encounter_pokemon(
            species="Rattata", level=5, source_kind="wild", nature="Hardy",
            ivs=[0] * 6, evs=[0] * 6, current_hp=1, status="psn", move_names=["Quickattack"],
        )
        target = Pokemon("Rattata", hp=1, max_hp=get_max_hp(encounter), model_id=f"encounter:{encounter.pk}")
        target.setStatus("slp", effect="move:rest")
        target.tempvals["sleep_turns"] = 1
        result = finalize_wild_capture(target_poke=target, player=self.player, trainer=self.trainer)
        _, owned_id = parse_pokemon_ref(result.owned_pokemon_id)
        caught = OwnedPokemon.objects.get(pk=owned_id)
        caught.refresh_from_db()
        self.assertEqual((caught.current_hp, caught.status, caught.sleep_turns), (1, "slp", 1))
        restored = build_battle_pokemon_from_model(caught)
        self.assertEqual((restored.status, restored.tempvals["sleep_turns"]), ("slp", 1))


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        from evennia.objects.models import ObjectDB

        from pokemon.battle.battledata import Pokemon
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle.engine import Action, ActionType, Battle, BattleParticipant, BattleType
        from pokemon.dex.functions.conditions_funcs import CONDITION_HANDLERS
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon, get_max_hp
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.storage import StorageBox, UserStorage
        from pokemon.models.trainer import Trainer
        from pokemon.services.capture import finalize_wild_capture
        from pokemon.services.encounters import create_encounter_pokemon
        from pokemon.services.placement import PlacementService
        from pokemon.services.pokemon_refs import parse_pokemon_ref
        from utils.fusion import get_battle_party_with_fusion
        from utils.pokemon_utils import build_battle_pokemon_from_model

        unittest.main(verbosity=2)

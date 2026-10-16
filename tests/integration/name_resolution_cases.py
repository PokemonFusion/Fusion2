"""Real-model name lookup regressions in a disposable PostgreSQL schema."""

from __future__ import annotations

import math
import unittest
from types import SimpleNamespace
from uuid import uuid4

from isolated_postgres import IsolatedPostgres


class NameResolutionCases(unittest.TestCase):
    """Exercise name variants through production storage, menus and battles."""

    def setUp(self):
        """Create a character and trainer only within the isolated schema."""
        character = ObjectDB.objects.create(db_key="names-" + uuid4().hex)
        self.trainer = Trainer.objects.create(user=character, trainer_number=Trainer.objects.count() + 1)
        self.storage = UserStorage.objects.create(user=character)
        self.messages = []
        self.player = SimpleNamespace(
            key=character.key, trainer=self.trainer, storage=self.storage,
            db=character.db, ndb=SimpleNamespace(), msg=self.messages.append,
        )

    def pokemon(self, species="Squirtle", *, moves=None):
        """Create a real party Pokemon with deterministic stat inputs."""
        return create_owned_pokemon(
            species, self.trainer, 5, nature="Hardy", gender="M",
            ivs=[12, 8, 20, 14, 10, 16], evs=[0, 0, 0, 0, 0, 0],
            active_move_names=moves or ["Watergun"],
        )

    def test_spaced_species_keep_stats_types_and_stored_spelling(self):
        """Display names resolve to the same stats and typing as dex keys."""
        for display, key in [
            ("Mr. Mime", "Mrmime"), ("Type: Null", "Typenull"),
            ("Tapu Koko", "Tapukoko"), ("Farfetch’d", "Farfetchd"),
        ]:
            with self.subTest(species=display):
                owned = self.pokemon(display, moves=["Tackle"])
                self.assertEqual(OwnedPokemon.objects.filter(pk=owned.pk).values_list("species", flat=True).get(), display)
                self.assertEqual(owned.types, POKEDEX[key].types)
                self.assertEqual(
                    calculate_stats(display, 5, {}, {}, "Hardy"),
                    calculate_stats(key, 5, {}, {}, "Hardy"),
                )
                battle = build_battle_pokemon_from_model(owned)
                self.assertEqual(battle.max_hp, get_max_hp(owned))
                self.assertEqual(battle.types, owned.types)

    def test_nickname_with_spaces_preserves_species_in_battle_and_restore(self):
        """A nickname is display text and must not replace the battle species."""
        owned = self.pokemon("Mr. Mime", moves=["Tackle"])
        owned.nickname = "Stage Star"
        owned.save(update_fields=["nickname"])
        battle = build_battle_pokemon_from_model(owned)
        restored = Pokemon.from_dict(battle.to_dict())
        for mon in (battle, restored):
            self.assertEqual(mon.name, "Stage Star")
            self.assertEqual(mon.species, "Mr. Mime")
            self.assertEqual(mon.types, POKEDEX["Mrmime"].types)
            self.assertEqual(mon.max_hp, get_max_hp(owned))

    def test_learning_aliases_does_not_duplicate_records_or_active_slots(self):
        """Teaching a spaced spelling reuses the already learned move object."""
        owned = self.pokemon()
        move_ids = set(owned.learned_moves.values_list("pk", flat=True))
        slots = list(owned.activemoveslot_set.values_list("move_id", flat=True))
        count = Move.objects.count()
        for name in ("Water Gun", "WATER  GUN", "watergun"):
            learn_move(owned, name)
        self.assertEqual(set(owned.learned_moves.values_list("pk", flat=True)), move_ids)
        self.assertEqual(list(owned.activemoveslot_set.values_list("move_id", flat=True)), slots)
        self.assertEqual(Move.objects.count(), count)

    def test_global_legacy_move_spelling_is_reused(self):
        """New learning must not split an existing hyphenated move record."""
        legacy, _ = Move.objects.get_or_create(name="Double-Edge")
        count = Move.objects.count()
        self.assertEqual(get_or_create_move("Doubleedge").pk, legacy.pk)
        self.assertEqual(Move.objects.count(), count)

    def test_moveset_edit_reuses_learned_move_and_pp_boost(self):
        """Editing with a display name preserves the move FK and its PP bonus."""
        owned = self.pokemon()
        original = owned.activemoveslot_set.get().move_id
        self.assertTrue(owned.apply_pp_up("Water Gun"))
        self.player.ndb.ms_pokemon = owned
        self.player.ndb.ms_index = 0
        moveset_manager.node_edit(self.player, "Water Gun")
        self.assertEqual(owned.active_moveset.slots.get().move_id, original)
        self.assertEqual(owned.activemoveslot_set.get().move_id, original)
        self.assertEqual(owned.pp_boosts.get(move_id=original).bonus_pp, 1)
        self.assertEqual(owned.activemoveslot_set.values_list("current_pp", flat=True).get(), 26)

    def test_moveset_edit_rejects_equivalent_duplicates_before_writing(self):
        """Two spellings of the same learned move cannot occupy two slots."""
        owned = self.pokemon()
        before = list(owned.active_moveset.slots.values_list("move_id", flat=True))
        self.player.ndb.ms_pokemon = owned
        self.player.ndb.ms_index = 0
        moveset_manager.node_edit(self.player, "Water Gun, Watergun")
        self.assertEqual(list(owned.active_moveset.slots.values_list("move_id", flat=True)), before)
        self.assertIn("Duplicate moves are not allowed.", self.messages)

    def test_seen_and_caught_species_aliases_use_one_record(self):
        """Trainer progress resolves both compact and punctuated species names."""
        entry, _ = SpeciesEntry.objects.get_or_create(name="Mr. Mime", defaults={"dex_id": 122})
        for name in ("Mrmime", "MR MIME", "Mr. Mime"):
            self.trainer.log_seen_pokemon(name)
            self.trainer.log_caught_pokemon(name)
        self.assertEqual(list(self.trainer.seen_pokemon.values_list("pk", flat=True)), [entry.pk])

    def test_spaced_opponent_name_awards_exp_and_evs(self):
        """Faint rewards use species identity even when the display name differs."""
        owned = self.pokemon()
        initial = owned.total_exp
        active = build_battle_pokemon_from_model(owned)
        target = Pokemon("Mr. Mime", level=5, hp=0)
        target.name = "Stage Star"
        player = BattleParticipant("Player", [active], player=self.player)
        opponent = BattleParticipant("Opponent", [target], is_ai=True)
        player.active = [active]
        opponent.active = [target]
        Battle(BattleType.WILD, [player, opponent]).run_faint()
        stored = OwnedPokemon.objects.filter(pk=owned.pk).values("total_exp", "evs").get()
        info = resolve_dex_entry(GAIN_INFO, "Mr. Mime")
        self.assertEqual(stored["total_exp"], initial + math.floor(info["exp"] * 5 / 7))
        self.assertGreater(sum(stored["evs"]), 0)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        from evennia.objects.models import ObjectDB

        from menus import moveset_manager
        from pokemon.battle.battledata import Pokemon
        from pokemon.battle.engine import Battle, BattleParticipant, BattleType
        from pokemon.dex import POKEDEX
        from pokemon.dex.exp_ev_yields import GAIN_INFO
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon, get_max_hp
        from pokemon.models.core import OwnedPokemon, SpeciesEntry
        from pokemon.models.moves import Move
        from pokemon.models.stats import calculate_stats
        from pokemon.models.storage import UserStorage
        from pokemon.models.trainer import Trainer
        from pokemon.names import resolve_dex_entry
        from pokemon.services.move_management import get_or_create_move
        from pokemon.utils.move_learning import learn_move
        from utils.pokemon_utils import build_battle_pokemon_from_model

        unittest.main(verbosity=2)

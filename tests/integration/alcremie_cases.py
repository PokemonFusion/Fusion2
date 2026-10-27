"""Exercise Sweet evolution through production commands/models in isolated PG.

Run with an explicit PF2_TEST_POSTGRES_DSN. No game database or migrations are
used. Session transport is captured; gameplay command/service code is real.
"""

import json
import re
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
from pokemon.evolution_forms import AlcremieEvolution

WALKTHROUGH = []


class PlayerView:
    """Bind real ownership/attributes while capturing an ordinary command session."""

    def __init__(self, character, trainer, storage):
        """Only the session output is replaced; every persisted object is real."""
        self.pk = self.id = character.pk
        self.key = self.name = character.key
        self.db, self.ndb = character.db, character.ndb
        self.attributes = character.attributes
        self.trainer, self.storage = trainer, storage
        self.location = None
        self.messages = []

    def msg(self, text, **kwargs):
        """Retain command output without creating a live Evennia session."""
        self.messages.append(str(text))

    def get_pokemon_by_id(self, value):
        """Use the shipped player's complete-ID ownership lookup."""
        return User.get_pokemon_by_id(self, value)


class AlcremieCases(unittest.TestCase):
    """Prove all cosmetics, durable state and atomic failure/replay boundaries."""

    def setUp(self):
        """Place one fresh Milcery in a gapped party with meaningful saved state."""
        self.character = ObjectDB.objects.create(db_key="alcremie-" + uuid4().hex)
        self.trainer = Trainer.objects.create(user=self.character, trainer_number=Trainer.objects.count() + 1)
        self.storage = UserStorage.objects.create(user=self.character)
        self.mon = create_owned_pokemon(
            "Milcery", self.trainer, 30, gender="F", ability="Sweet Veil", nature="Hardy",
            ivs=[0] * 6, evs=[0, 8, 0, 12, 0, 0], active_move_names=["Tackle", "Watergun"],
        )
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(
            nickname="Cream", status="brn", current_hp=3, friendship=137,
            flags=["keep-this-flag"],
        )
        PlacementService(self.storage).to_party(self.mon, slot=3)
        ActiveMoveslot.objects.filter(pokemon=self.mon).update(current_pp=7)
        OwnedPokemon.flush_cached_instance(self.mon)
        self.mon = OwnedPokemon.objects.get(pk=self.mon.pk)
        self.caller = PlayerView(self.character, self.trainer, self.storage)

    def row(self, mon=None):
        """Bypass the shared identity map and read actual SQL values."""
        return OwnedPokemon.objects.filter(pk=(mon or self.mon).pk).values().get()

    def command(self, kind, args):
        """Run normal +hold, +evolve or +party parse/func entry points."""
        cls = {"hold": CmdSetHoldItem, "evolve": CmdEvolvePokemon, "party": CmdSheetPokemon}[kind]
        command = cls()
        command.caller, command.args = self.caller, args
        command.parse()
        command.func()
        return self.caller.messages[-1]

    def equip(self, sweet="Berry Sweet", copies=2):
        """Move a real inventory Sweet into the held slot via the shipped command."""
        self.trainer.add_item(sweet, copies)
        output = self.command("hold", "3=" + sweet)
        self.assertIn("now holding " + sweet, output)
        self.assertEqual(self.row()["held_item"], sweet)
        self.assertEqual(self.trainer.get_item_quantity(sweet), copies - 1)

    def preserved(self):
        """Capture identity, every gameplay scalar, placement, moves and PP."""
        row = self.row()
        for key in ("species", "ability", "held_item", "type_", "flags"):
            row.pop(key, None)
        return row, list(ActiveMoveslot.objects.filter(pokemon=self.mon).order_by("slot").values()), list(
            self.storage.placements.filter(pokemon=self.mon).values())

    def combination(self, sweet, form):
        """Prove one supported Sweet/cream through commands and a fresh SQL read."""
        initial_sheet = self.command("party", "3")
        identifier = re.search(r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", strip_ansi(initial_sheet))
        self.assertIsNotNone(identifier, "Player must be able to discover the evolution ID")
        pokemon_id = identifier.group()
        self.assertEqual(pokemon_id, str(self.mon.pk))
        ability = "Aroma Veil" if (AlcremieEvolution.sweets.index(sweet) + AlcremieEvolution.forms().index(form)) % 2 else "Sweet Veil"
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(ability=ability)
        self.equip(sweet)
        before = self.preserved()
        args = pokemon_id + ("=" + form if form != "Alcremie" else "")
        output = self.command("evolve", args)
        self.assertIn("evolved into Alcremie", output)
        after = self.row()
        self.assertEqual((after["species"], after["ability"], after["held_item"]), ("Alcremie", ability, ""))
        appearance = {"form": form, "sweet": sweet}
        self.assertEqual(AlcremieEvolution.appearance(SimpleNamespace(**after)), appearance)
        self.assertIn("keep-this-flag", after["flags"])
        self.assertEqual(self.preserved(), before)
        self.assertEqual(self.trainer.get_item_quantity(sweet), 1)
        # Discard the shared instance and rebuild from SQL before rendering.
        previous = self.mon
        OwnedPokemon.flush_cached_instance(previous)
        self.mon = OwnedPokemon.objects.get(pk=previous.pk)
        self.assertIsNot(self.mon, previous)
        self.assertEqual(AlcremieEvolution.appearance(self.mon), appearance)
        sheet = self.command("party", "3")
        cream = "Vanilla Cream" if form == "Alcremie" else form.removeprefix("Alcremie-").replace("-", " ")
        self.assertIn(cream, sheet)
        self.assertIn(sweet, sheet)
        self.assertIn("Nothing", sheet)
        completed = self.row()
        self.command("evolve", args)
        self.assertIn("already completed", self.caller.messages[-1])
        self.assertEqual(self.row(), completed)
        self.assertEqual(self.trainer.get_item_quantity(sweet), 1)
        if form == "Alcremie-Ruby-Cream":
            WALKTHROUGH.append({"sweet": sweet, "commands": ["+party 3", "+hold 3=" + sweet, "+evolve " + args, "+party 3"],
                                "discovered_id": pokemon_id,
                                "evolution_output": output, "appearance": appearance,
                                "held_after": after["held_item"], "bag_after": 1, "sheet": sheet})

    def test_missing_wrong_held_item_and_bag_only_are_safe(self):
        """A bag Sweet is never silently spent as a spin/equip substitute."""
        self.trainer.add_item("Berry Sweet", 2)
        before = self.row()
        self.command("evolve", str(self.mon.pk))
        self.command("evolve", str(self.mon.pk) + " Berry Sweet")
        self.command("evolve", str(self.mon.pk) + " Berry Sweet=Alcremie-Ruby-Cream")
        self.assertEqual(self.row(), before)
        self.assertEqual(self.trainer.get_item_quantity("Berry Sweet"), 2)
        for item in ("Sweet Apple", "Oran Berry", "Everstone"):
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(held_item=item)
            before = self.row()
            self.command("evolve", str(self.mon.pk))
            self.assertEqual(self.row(), before)

    def test_wrong_species_invalid_targets_and_partial_names_preserve_sweet(self):
        """Never transform a foreign holder or enable an unlisted/Gmax appearance."""
        self.equip()
        for target in ("Alcremie-Gmax", "Alcremie-Chocolate-Cream", "Ruby Cream", "Alcremie-Ruby", "Pikachu"):
            before = self.row()
            self.command("evolve", f"{self.mon.pk}={target}")
            self.assertEqual(self.row(), before)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(species="Pikachu")
        before = self.row()
        self.command("evolve", f"{self.mon.pk}=Alcremie")
        self.assertEqual(self.row(), before)

    def test_egg_and_fusion_reservation_reject_without_consuming(self):
        """Existing lifecycle restrictions apply to held Sweet consumption."""
        self.equip()
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(is_egg=True)
        before = self.row()
        self.command("evolve", str(self.mon.pk))
        self.assertEqual(self.row(), before)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(is_egg=False)
        PlacementService(self.storage).reserve_for_fusion(self.mon)
        before = self.row()
        self.command("evolve", str(self.mon.pk))
        self.assertEqual(self.row(), before)

    def test_battle_lock_blocks_both_player_command_and_service(self):
        """Reject command entry and a battle starting before the locked write."""
        self.equip()
        before = self.row()
        self.caller.db.battle_lock = "fixture-battle"
        self.command("evolve", str(self.mon.pk))
        with self.assertRaises(EvolutionError):
            EvolutionService(self.caller).evolve(self.mon)
        self.assertEqual(self.row(), before)
        self.assertEqual(self.trainer.get_item_quantity("Berry Sweet"), 1)

    def test_failed_save_restores_held_sweet_appearance_receipt_and_shared_cache(self):
        """The single atomic save owns both cosmetics and consumption."""
        self.equip("Star Sweet")
        before = self.row()
        with patch.object(OwnedPokemon, "save", side_effect=RuntimeError("fixture save failure")):
            self.command("evolve", f"{self.mon.pk}=Alcremie-Rainbow-Swirl")
        self.assertIn("Evolution failed", self.caller.messages[-1])
        self.assertEqual(self.row(), before)
        self.assertEqual((self.mon.species, self.mon.held_item, self.mon.flags),
                         (before["species"], before["held_item"], before["flags"]))
        self.command("evolve", f"{self.mon.pk}=Alcremie-Rainbow-Swirl")
        self.assertEqual(self.row()["species"], "Alcremie")
        self.assertEqual(self.trainer.get_item_quantity("Star Sweet"), 1)

    def test_fresh_locked_state_overrules_unsaved_source_and_held_values(self):
        """Validate persisted item/species, not a stale shared model reference."""
        self.equip("Clover Sweet")
        self.mon.species, self.mon.held_item = "Pikachu", "Leftovers"
        self.assertEqual(EvolutionService(self.caller).evolve(self.mon), "Alcremie")
        self.assertEqual(AlcremieEvolution.appearance(SimpleNamespace(**self.row()))["sweet"], "Clover Sweet")

    def test_foreign_owner_and_changed_placement_are_rejected(self):
        """A successful prior command cannot authorize another owner's row."""
        self.equip()
        other = ObjectDB.objects.create(db_key="foreign-" + uuid4().hex)
        self.caller.pk = other.pk
        before = self.row()
        with self.assertRaises(EvolutionError):
            EvolutionService(self.caller).evolve(self.mon)
        self.assertEqual(self.row(), before)

    def test_replay_with_a_new_sweet_cannot_redecorate_or_consume_it(self):
        """Both an exact retry and a different cosmetic target are harmless."""
        self.equip()
        args = f"{self.mon.pk}=Alcremie-Ruby-Cream"
        self.command("evolve", args)
        self.equip("Flower Sweet")
        before = self.row()
        self.command("evolve", args)
        self.command("evolve", f"{self.mon.pk}=Alcremie-Matcha-Cream")
        self.assertEqual(self.row(), before)
        self.assertEqual(self.row()["held_item"], "Flower Sweet")

    def test_cosmetic_tags_cannot_replace_a_real_held_sweet(self):
        """Result metadata is never a player-supplied completion condition."""
        self.trainer.add_item("Berry Sweet", 2)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(flags=[
            "alcremie:form:Alcremie-Ruby-Cream", "alcremie:sweet:Berry Sweet", "spin:completed",
        ])
        before = self.row()
        self.command("evolve", str(self.mon.pk))
        self.assertEqual(self.row(), before)

    def test_normalized_full_cosmetic_name_and_ability_fallback(self):
        """Use the shared full-name policy and existing ability-slot fallback."""
        self.equip()
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(ability="unrecognized legacy ability")
        self.command("evolve", f"{self.mon.pk}=alcremie ruby cream")
        self.assertEqual(AlcremieEvolution.appearance(SimpleNamespace(**self.row()))["form"], "Alcremie-Ruby-Cream")
        self.assertEqual(self.row()["ability"], "Sweet Veil")

    def test_explicit_base_target_and_gender_condition(self):
        """An explicit Vanilla target works only with the saved gender condition."""
        self.equip()
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(gender="M")
        before = self.row()
        self.command("evolve", f"{self.mon.pk}=Alcremie")
        self.assertEqual(self.row(), before)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(gender="F")
        self.command("evolve", f"{self.mon.pk}=Alcremie")
        self.assertEqual(AlcremieEvolution.appearance(SimpleNamespace(**self.row()))["form"], "Alcremie")

    def test_cosmetic_selection_keeps_canonical_battle_stats_types_and_item(self):
        """A saved cream must not become an unsupported battle species name."""
        from pokemon.helpers.pokemon_helpers import get_max_hp, get_stats
        from utils.pokemon_utils import build_battle_pokemon_from_model

        self.equip()
        self.command("evolve", f"{self.mon.pk}=Alcremie-Rainbow-Swirl")
        OwnedPokemon.flush_cached_instance(self.mon)
        fresh = OwnedPokemon.objects.get(pk=self.mon.pk)
        battle_mon = build_battle_pokemon_from_model(fresh)
        self.assertEqual(str(battle_mon.species), "Alcremie")
        self.assertEqual(battle_mon.types, ["Fairy"])
        self.assertEqual(battle_mon.max_hp, get_max_hp(fresh))
        self.assertEqual(vars(battle_mon.base_stats), get_stats(fresh))
        self.assertFalse(battle_mon.item)

    def test_concurrent_identical_requests_consume_the_held_sweet_once(self):
        """Separate PostgreSQL connections serialize on the existing storage lock."""
        self.equip("Ribbon Sweet")
        barrier = Barrier(2)

        def evolve():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return EvolutionService(self.caller).evolve(self.mon, target="Alcremie-Caramel-Swirl")
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: evolve(), range(2)))
        self.assertCountEqual(results, ["Alcremie", None])
        self.assertEqual(self.row()["held_item"], "")
        self.assertEqual(self.trainer.get_item_quantity("Ribbon Sweet"), 1)
        self.assertEqual(len([f for f in self.row()["flags"] if f.startswith("evo:")]), 1)


def combination_test(sweet, form):
    """Create one independently reported production-model test per combination."""
    def test(self):
        """Evolve and reload a supported Sweet/cream pair via player commands."""
        self.combination(sweet, form)
    return test


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from evennia.commands.command import Command
        with patch.object(evennia, "Command", Command):
            from commands.player.cmd_learn_evolve import CmdEvolvePokemon
            from commands.player.cmd_party import CmdSetHoldItem
            from commands.player.cmd_sheet import CmdSheetPokemon
        from django.db import close_old_connections, connections
        from evennia.objects.models import ObjectDB
        from evennia.utils.ansi import strip_ansi
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.models.storage import UserStorage
        from pokemon.models.trainer import Trainer
        from pokemon.services.evolution import EvolutionError, EvolutionService
        from pokemon.services.placement import PlacementService
        from pokemon.user import User

        for index, sweet in enumerate(AlcremieEvolution.sweets):
            for number, form in enumerate(AlcremieEvolution.forms()):
                setattr(AlcremieCases, f"test_combination_{index}_{number}", combination_test(sweet, form))
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AlcremieCases))
        print("ALCREMIE_PLAYER_WALKTHROUGH " + json.dumps(WALKTHROUGH))
        raise SystemExit(not result.wasSuccessful())

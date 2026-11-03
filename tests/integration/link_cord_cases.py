"""Real bag-cord commands and transactions in an explicit disposable PG schema.

Only transport is captured. Fixture setup grants bag copies directly and does
not install a public item source, run migrations or touch human game data.
"""

import json
import re
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
from ui_cases import PlayerView as SessionTransport

WALKTHROUGH = []


class PlayerView(SessionTransport):
    """Capture session output while retaining the production ownership lookup."""

    def get_pokemon_by_id(self, value):
        """Delegate complete-ID resolution to the ordinary player implementation."""
        return User.get_pokemon_by_id(self, value)


class LinkCordCases(unittest.TestCase):
    """Verify exact transitions, conservation and shared lifecycle boundaries."""

    def setUp(self):
        """Create tagged disposable state with a gapped party and two bag cords."""
        self.character = ObjectDB.objects.create(db_key="link-cord-owner-" + uuid4().hex)
        self.trainer = Trainer.objects.create(
            user=self.character, trainer_number=Trainer.objects.count() + 1,
        )
        self.storage = UserStorage.objects.create(user=self.character)
        self.caller = self.player(self.character, self.trainer, self.storage)
        self.mon = create_owned_pokemon(
            "Haunter", self.trainer, 30, ability="Levitate", nature="Hardy",
            ivs=[1, 2, 3, 4, 5, 6], evs=[0, 8, 0, 12, 0, 0],
            active_move_names=["Tackle", "Watergun"], held_item="Leftovers",
        )
        PlacementService(self.storage).to_party(self.mon, slot=3)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(
            nickname="Buddy", current_hp=3, status="slp", sleep_turns=2,
            friendship=137, flags=["keep-this-flag"],
        )
        ActiveMoveslot.objects.filter(pokemon=self.mon).update(current_pp=7)
        self.reload()
        self.trainer.add_item("Link Cord", 2)

    @staticmethod
    def player(character, trainer, storage):
        """Bind a fresh ordinary transport without any server or staff session."""
        player = PlayerView(character, trainer, storage)
        player.pk, player.location = character.pk, None
        return player

    def reload(self):
        """Discard the shared Pokemon object and reload persisted state."""
        previous = self.mon
        OwnedPokemon.flush_cached_instance(previous)
        self.mon = OwnedPokemon.objects.get(pk=previous.pk)
        self.assertIsNot(self.mon, previous)

    def row(self):
        """Bypass Evennia's identity map for authoritative SQL assertions."""
        return OwnedPokemon.objects.filter(pk=self.mon.pk).values().get()

    def quantity(self):
        """Count actual normalized bag entries through the trainer API."""
        return self.trainer.get_item_quantity("Link Cord")

    def command(self, kind, args):
        """Run normal command parsing and execution with captured output."""
        command = COMMANDS[kind]()
        command.caller, command.args = self.caller, args
        command.parse()
        command.func()
        return self.caller.messages[-1]

    def evolve(self, suffix=" Link Cord"):
        """Submit a complete current Pokemon ID to the normal evolution command."""
        return self.command("evolve", str(self.mon.pk) + suffix)

    def action(self, mon=None, target=None):
        """Use the same locked production service for concurrent requests."""
        return EvolutionService(self.caller).evolve(mon or self.mon, item="Link Cord", target=target)

    def preserved(self):
        """Snapshot unrelated scalars, moves/PP, placement and legacy mirrors."""
        row = self.row()
        for key in ("species", "ability", "type_", "flags"):
            row.pop(key, None)
        return (
            row, list(ActiveMoveslot.objects.filter(pokemon=self.mon).order_by("slot").values()),
            list(self.storage.placements.filter(pokemon=self.mon).values()),
            list(self.mon.active_slots.values()), list(self.mon.stored_users.values_list("pk", flat=True)),
            list(self.mon.boxes.values_list("pk", flat=True)),
        )

    def unchanged(self, suffix=" Link Cord"):
        """Rejected requests change neither saved Pokemon nor bag quantity."""
        before, quantity = self.row(), self.quantity()
        output = self.evolve(suffix)
        self.assertEqual(self.row(), before)
        self.assertEqual(self.quantity(), quantity)
        return output

    def mapping(self, source, target):
        """Inspect the item/ID, evolve, rebuild transport and retry one mapping."""
        abilities = lookup_species(source).raw["abilities"]
        slot = "H" if "H" in abilities else "0"
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(species=source, ability=abilities[slot])
        self.reload()
        self.assertEqual(OwnedPokemon.objects.filter(trainer=self.trainer).count(), 1)
        self.assertIn("Link Cord x2", self.command("inventory", ""))
        detail = self.command("itemdex", "Link Cord")
        self.assertIn("Category: Evolution Items", detail)
        self.assertIn("+evolve", detail)
        sheet = self.command("party", "3")
        identifier = re.search(r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", strip_ansi(sheet))
        self.assertIsNotNone(identifier)
        self.assertEqual(identifier.group(), str(self.mon.pk))
        before, maximum = self.preserved(), get_max_hp(self.mon)
        output = self.evolve(" Link Cord=" + target)
        self.assertIn("evolved into " + target, output)
        self.assertEqual(self.row()["species"], target)
        target_abilities = lookup_species(target).raw["abilities"]
        self.assertEqual(self.row()["ability"], target_abilities.get(slot, target_abilities["0"]))
        self.assertEqual(self.quantity(), 1)
        self.assertEqual(self.preserved(), before)
        self.assertIn("keep-this-flag", self.row()["flags"])
        self.assertEqual(len([flag for flag in self.row()["flags"] if flag.startswith("evo:")]), 1)
        self.reload()
        self.caller = self.player(self.character, Trainer.objects.get(pk=self.trainer.pk),
                                  UserStorage.objects.get(pk=self.storage.pk))
        result_sheet = self.command("party", "3")
        self.assertIn(target, result_sheet)
        self.assertIn(str(self.mon.pk), result_sheet)
        self.assertEqual(list(self.mon.types), list(lookup_species(target).types))
        self.assertIn("already completed", self.unchanged(" link-cord=" + target.lower()))
        WALKTHROUGH.append({"source": source, "target": target, "id": str(self.mon.pk),
                            "bag_after": 1, "held_after": self.row()["held_item"],
                            "max_hp_before": maximum, "max_hp_after": get_max_hp(self.mon),
                            "output": output, "SQL_reload_and_retry": True,
                            "owner_placement_moves_and_other_state_preserved": True})

    def test_no_bag_input_missing_copy_and_partial_names_are_inert(self):
        """The explicit action and one actual bag copy are both required."""
        for suffix in ("", "=Gengar", " Link", " Cord", " Linking Cord", " Link Cord=Geng"):
            self.unchanged(suffix)
        self.trainer.remove_item("Link Cord", 2)
        self.assertIn("do not have", self.unchanged())

    def test_held_only_cord_cannot_activate_and_can_be_returned(self):
        """Equipping is reversible and does not manufacture a bag-use copy."""
        self.command("hold", "3=Link Cord")
        self.trainer.remove_item("Link Cord")
        self.unchanged("")
        self.unchanged()
        self.assertEqual(self.row()["held_item"], "Link Cord")
        self.command("hold", "3=")
        self.assertEqual(self.quantity(), 1)

    def test_bag_use_keeps_a_separate_equipped_cord(self):
        """Only the bag copy is consumed even when another copy is held."""
        self.command("hold", "3=Link Cord")
        self.assertIn("evolved into Gengar", self.evolve())
        self.assertEqual(self.row()["held_item"], "Link Cord")
        self.assertEqual(self.quantity(), 0)

    def test_cross_region_size_and_foreign_targets_consume_nothing(self):
        """Complete but mismatched target names cannot change native form or size."""
        for source, target in (("Graveler", "Golem-Alola"), ("Graveler-Alola", "Golem"),
                               ("Pumpkaboo", "Gourgeist-Super"), ("Pumpkaboo-Super", "Gourgeist"),
                               ("Pumpkaboo-Small", "Gourgeist-Large"),
                               ("Pumpkaboo-Large", "Gourgeist-Small"), ("Haunter", "Alakazam")):
            with self.subTest(source=source, target=target):
                OwnedPokemon.objects.filter(pk=self.mon.pk).update(species=source)
                self.unchanged(" Link Cord=" + target)

    def test_independent_bug_evolution_does_not_change_the_other_pokemon(self):
        """One use changes only its selected bug, and two evolutions cost two cords."""
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(species="Karrablast", ability="Swarm")
        other = create_owned_pokemon("Shelmet", self.trainer, 30, nature="Hardy", ability="Hydration",
                                     ivs=[0] * 6, evs=[0] * 6, active_move_names=["Tackle"])
        before = OwnedPokemon.objects.filter(pk=other.pk).values().get()
        self.assertIn("evolved into Escavalier", self.evolve())
        self.assertEqual(OwnedPokemon.objects.filter(pk=other.pk).values().get(), before)
        self.assertEqual(self.quantity(), 1)
        self.assertEqual(self.action(other), "Accelgor")
        self.assertEqual(self.quantity(), 0)
        self.assertEqual(self.row()["species"], "Escavalier")

    def test_everstone_egg_battle_and_invalid_level_guards(self):
        """The new rule cannot bypass ordinary lifecycle or saved-level limits."""
        for field, value in (("held_item", "Everstone"), ("is_egg", True), ("level", 0), ("level", 101)):
            original = self.row()[field]
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(**{field: value})
            self.unchanged()
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(**{field: original})
        self.caller.db.battle_lock = "link-cord-fixture-battle"
        self.unchanged()
        with self.assertRaises(EvolutionError):
            self.action()

    def test_fusion_and_market_reservations_block_consumption(self):
        """Shared placement and system claims protect the same owned identity."""
        token = uuid4()
        PokemonReservations(self.character).claim("market", [self.mon.pk], token)
        self.unchanged()
        PokemonReservations(self.character).release("market", token)
        PlacementService(self.storage).reserve_for_fusion(self.mon)
        self.unchanged()

    def test_foreign_owner_and_conflicting_placement_fail_closed(self):
        """A known UUID cannot authorize another owner's evolution or custody repair."""
        other = ObjectDB.objects.create(db_key="link-cord-foreign-" + uuid4().hex)
        trainer = Trainer.objects.create(user=other, trainer_number=Trainer.objects.count() + 1)
        storage = UserStorage.objects.create(user=other)
        trainer.add_item("Link Cord")
        self.caller = self.player(other, trainer, storage)
        self.assertIn("No such", self.unchanged())
        with self.assertRaises(EvolutionError):
            self.action()
        self.assertEqual(trainer.get_item_quantity("Link Cord"), 1)
        self.caller = self.player(self.character, self.trainer, self.storage)
        self.storage.placements.filter(pokemon=self.mon).update(storage=storage)
        self.unchanged()

    def test_boxed_evolution_retains_all_placement_and_state(self):
        """An owned boxed source stays in its existing box and position."""
        PlacementService(self.storage).to_box(self.mon)
        before = self.preserved()
        self.assertIn("evolved into Gengar", self.evolve())
        self.assertEqual(self.preserved(), before)

    def test_fresh_locked_source_overrules_unsaved_and_stale_cached_species(self):
        """Client/cached changes cannot create or remove native source eligibility."""
        self.mon.species, self.mon.held_item = "Pikachu", "Everstone"
        self.assertEqual(self.action(), "Gengar")
        self.assertEqual(self.row()["held_item"], "Leftovers")
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(species="Pikachu", flags=[])
        self.mon.species = "Haunter"
        with self.assertRaises(EvolutionError):
            self.action()
        self.assertEqual(self.row()["species"], "Pikachu")
        self.assertEqual(self.quantity(), 1)

    def test_failed_save_rolls_back_actual_debit_species_receipt_and_cache(self):
        """A post-SQL failure restores all state and permits a real retry."""
        before, preserved = self.row(), self.preserved()
        original = OwnedPokemon.save

        def fail_after_save(mon, *args, **kwargs):
            """Inject failure after the real write, without faking a success."""
            original(mon, *args, **kwargs)
            raise RuntimeError("link-cord fixture failure after SQL save")

        with patch.object(OwnedPokemon, "save", fail_after_save):
            self.assertIn("Evolution failed", self.evolve())
        self.assertEqual(self.row(), before)
        self.assertEqual(self.preserved(), preserved)
        self.assertEqual((self.mon.species, self.mon.flags), (before["species"], before["flags"]))
        self.assertEqual(self.quantity(), 2)
        self.assertIn("evolved into Gengar", self.evolve())

    def test_alias_inventory_entries_debit_exactly_one_total(self):
        """Legacy complete spellings remain the same bag resource."""
        self.trainer.remove_item("Link Cord", 2)
        InventoryEntry.objects.create(owner=self.trainer, item_name="Link Cord", quantity=1)
        InventoryEntry.objects.create(owner=self.trainer, item_name="link-cord", quantity=2)
        self.assertIn("evolved into Gengar", self.evolve())
        self.assertEqual(self.quantity(), 2)

    def race(self, first, second):
        """Synchronize real requests on independent PostgreSQL connections."""
        barrier = Barrier(2)

        def run(action):
            """Keep each worker's transaction and connection independent."""
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    return action()
                except EvolutionError:
                    return "rejected"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(run, (first, second)))

    def test_concurrent_identical_requests_debit_once(self):
        """One stored receipt survives duplicate completion on independent connections."""
        self.assertCountEqual(self.race(self.action, self.action), ["Gengar", None])
        self.assertEqual(self.quantity(), 1)

    def test_distinct_requests_compete_for_last_bag_copy(self):
        """The final bag copy cannot evolve two different owned Pokemon."""
        other = create_owned_pokemon("Haunter", self.trainer, 30, nature="Hardy", ability="Levitate",
                                     ivs=[0] * 6, evs=[0] * 6, active_move_names=["Tackle"])
        self.trainer.remove_item("Link Cord")
        self.assertCountEqual(self.race(self.action, lambda: self.action(other)), ["Gengar", "rejected"])
        self.assertEqual(self.quantity(), 0)
        self.assertEqual(OwnedPokemon.objects.filter(trainer=self.trainer, species="Gengar").count(), 1)

    def test_concurrent_reservation_has_one_legal_serial_order(self):
        """A reservation that commits first prevents a subsequent cord debit."""
        results = self.race(self.action, lambda: PlacementService(self.storage).reserve_for_fusion(self.mon))
        evolved = self.row()["species"] == "Gengar"
        self.assertIn("Gengar" if evolved else "rejected", results)
        self.assertEqual(self.quantity(), 1 if evolved else 2)
        self.assertEqual(PokemonPlacement.objects.get(pokemon=self.mon).location_type, "fusion")


def mapping_test(source, target):
    """Give each approved mapping its own reported ordinary-command test."""
    def test(self):
        """Run the complete player-visible transition and persisted retry."""
        self.mapping(source, target)
    return test


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from evennia.commands.command import Command
        with patch.object(evennia, "Command", Command):
            from commands.player.cmd_inventory import CmdInventory
            from commands.player.cmd_learn_evolve import CmdEvolvePokemon
            from commands.player.cmd_party import CmdSetHoldItem
            from commands.player.cmd_pokedex import CmdItemdexSearch
            from commands.player.cmd_sheet import CmdSheetPokemon
        from django.db import close_old_connections, connections
        from evennia.objects.models import ObjectDB
        from evennia.utils.ansi import strip_ansi
        from pokemon.data.evolution import lookup_species
        from pokemon.evolution_items import LinkCordEvolution
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon, get_max_hp
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.models.storage import PokemonPlacement, UserStorage
        from pokemon.models.trainer import InventoryEntry, Trainer
        from pokemon.services.evolution import EvolutionError, EvolutionService
        from pokemon.services.ownership import PokemonReservations
        from pokemon.services.placement import PlacementService
        from pokemon.user import User

        COMMANDS = {"evolve": CmdEvolvePokemon, "hold": CmdSetHoldItem, "inventory": CmdInventory,
                    "itemdex": CmdItemdexSearch, "party": CmdSheetPokemon}
        for source, target in LinkCordEvolution.transitions:
            setattr(LinkCordCases, "test_mapping_" + target.replace("-", "_"), mapping_test(source, target))
        result = unittest.TextTestRunner(verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(LinkCordCases))
        print("LINK_CORD_PLAYER_WALKTHROUGH " + json.dumps(WALKTHROUGH))
        raise SystemExit(not result.wasSuccessful())

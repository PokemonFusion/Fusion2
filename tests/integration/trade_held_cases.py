"""Exercise existing trade-held equivalents through real commands and SQL.

Requires PF2_TEST_POSTGRES_DSN; session transport is captured, gameplay is real.
The isolated schema is removed on exit without touching game data or migrations.
"""

import json
import re
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
from pokemon.evolution_items import TradeHeldEvolution

WALKTHROUGH = []


class PlayerView:
    """Use real ownership, storage and attributes with captured session output."""

    def __init__(self, character, trainer, storage):
        """Bind an ordinary player without any staff access or transport server."""
        self.pk = self.id = character.pk
        self.key = self.name = character.key
        self.db, self.ndb = character.db, character.ndb
        self.attributes = character.attributes
        self.trainer, self.storage = trainer, storage
        self.location = None
        self.messages = []

    def msg(self, text, **kwargs):
        """Capture the normal command result for the walkthrough report."""
        self.messages.append(str(text))

    def get_pokemon_by_id(self, value):
        """Use the production complete-ID and owner lookup."""
        return User.get_pokemon_by_id(self, value)


class TradeHeldCases(unittest.TestCase):
    """Assert player-visible success, unchanged ownership and atomic failures."""

    def setUp(self):
        """Create a disposable owner and a gapped party with meaningful state."""
        self.character = ObjectDB.objects.create(db_key="trade-held-" + uuid4().hex)
        self.trainer = Trainer.objects.create(user=self.character, trainer_number=Trainer.objects.count() + 1)
        self.storage = UserStorage.objects.create(user=self.character)
        self.mon = create_owned_pokemon(
            "Scyther", self.trainer, 30, ability="Technician", nature="Hardy",
            ivs=[1, 2, 3, 4, 5, 6], evs=[0, 8, 0, 12, 0, 0],
            active_move_names=["Tackle", "Watergun"],
        )
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(
            nickname="Buddy", status="slp", sleep_turns=2, current_hp=3,
            friendship=137, flags=["keep-this-flag"],
        )
        PlacementService(self.storage).to_party(self.mon, slot=3)
        ActiveMoveslot.objects.filter(pokemon=self.mon).update(current_pp=7)
        self.reload()
        self.caller = PlayerView(self.character, self.trainer, self.storage)

    def reload(self):
        """Discard Evennia's shared instance and obtain a new model from SQL."""
        previous = self.mon
        OwnedPokemon.flush_cached_instance(previous)
        self.mon = OwnedPokemon.objects.get(pk=previous.pk)
        self.assertIsNot(self.mon, previous)

    def row(self):
        """Read actual database scalars without the identity map."""
        return OwnedPokemon.objects.filter(pk=self.mon.pk).values().get()

    def command(self, kind, args):
        """Invoke shipped command parsing and execution with the real caller."""
        cls = {"hold": CmdSetHoldItem, "evolve": CmdEvolvePokemon,
               "party": CmdSheetPokemon, "trade": CmdTradePokemon}[kind]
        command = cls()
        command.caller, command.args = self.caller, args
        command.parse()
        command.func()
        return self.caller.messages[-1]

    def equip(self, item="Metal Coat", copies=2):
        """Equip one real trainer-inventory copy through +hold."""
        previous = self.trainer.get_item_quantity(item)
        self.trainer.add_item(item, copies)
        self.assertIn("now holding " + item, self.command("hold", "3=" + item))
        self.assertEqual(self.row()["held_item"], item)
        self.assertEqual(self.trainer.get_item_quantity(item), previous + copies - 1)

    def preserved(self):
        """Capture all gameplay scalars, placement and compatibility mirrors."""
        row = self.row()
        for key in ("species", "ability", "held_item", "type_", "flags"):
            row.pop(key, None)
        return (
            row, list(ActiveMoveslot.objects.filter(pokemon=self.mon).order_by("slot").values()),
            list(self.storage.placements.filter(pokemon=self.mon).values()),
            list(self.mon.active_slots.values()), list(self.mon.stored_users.values_list("pk", flat=True)),
            list(self.mon.boxes.values_list("pk", flat=True)),
        )

    def mapping(self, source, target, item):
        """Exercise one complete player route and its durable result/retry."""
        abilities = lookup_species(source).raw["abilities"]
        slot = "H" if "H" in abilities else "0"
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(species=source, ability=abilities[slot])
        self.reload()
        sheet = self.command("party", "3")
        identifier = re.search(r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", strip_ansi(sheet))
        self.assertIsNotNone(identifier, "The full evolution ID must be discoverable by a player")
        pokemon_id = identifier.group()
        self.assertEqual(pokemon_id, str(self.mon.pk))
        self.equip(item)
        before = self.preserved()
        output = self.command("evolve", pokemon_id)
        self.assertIn("evolved into " + target, output)
        after = self.row()
        target_abilities = lookup_species(target).raw["abilities"]
        self.assertEqual((after["species"], after["held_item"], after["ability"]),
                         (target, "", target_abilities.get(slot, target_abilities["0"])))
        self.assertIn("keep-this-flag", after["flags"])
        self.assertEqual(len([flag for flag in after["flags"] if flag.startswith("evo:")]), 1)
        self.assertEqual(self.preserved(), before)
        self.assertEqual(self.trainer.get_item_quantity(item), 1)
        self.reload()
        result_sheet = self.command("party", "3")
        self.assertIn(target, result_sheet)
        self.assertIn(pokemon_id, result_sheet)
        self.assertIn("Nothing", result_sheet)
        completed = self.row()
        self.assertIn("already completed", self.command("evolve", pokemon_id))
        self.assertEqual(self.row(), completed)
        self.assertEqual(self.trainer.get_item_quantity(item), 1)
        WALKTHROUGH.append({"source": source, "target": target, "item": item,
                            "commands": ["+party 3", "+hold 3=" + item,
                                         "+evolve " + pokemon_id, "+party 3"],
                            "discovered_id": pokemon_id, "output": output,
                            "held_after": "", "bag_after": 1,
                            "owner_and_placement_unchanged": True, "sheet": result_sheet})

    def test_held_only_copy_needs_no_spare_bag_copy(self):
        """Consuming the held item must not require a second inventory copy."""
        self.equip(copies=1)
        self.command("evolve", str(self.mon.pk))
        self.assertEqual((self.row()["species"], self.row()["held_item"]), ("Scizor", ""))
        self.assertEqual(self.trainer.get_item_quantity("Metal Coat"), 0)

    def test_missing_wrong_item_everstone_and_bag_arguments_change_nothing(self):
        """A bag copy and partial item name cannot bypass the actual held slot."""
        self.trainer.add_item("Metal Coat", 2)
        for held in ("", "Leftovers", "Everstone", "Metal"):
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(held_item=held)
            before = self.row()
            for args in (str(self.mon.pk), f"{self.mon.pk} Metal Coat", f"{self.mon.pk}=Scizor"):
                self.command("evolve", args)
                self.assertEqual(self.row(), before)
            self.assertEqual(self.trainer.get_item_quantity("Metal Coat"), 2)

    def test_wrong_species_form_branch_and_partial_target_are_safe(self):
        """Shared items grant only exact, native direct successor transitions."""
        self.equip()
        for species, target in (("Pikachu", "Scizor"), ("Scyther", "Steelix"), ("Scyther", "Sciz"),
                                ("Slowpoke-Galar", "Slowking"), ("Clamperl", "Huntail")):
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(species=species)
            before = self.row()
            self.command("evolve", f"{self.mon.pk}={target}")
            self.assertEqual(self.row(), before)
        self.assertEqual(self.trainer.get_item_quantity("Metal Coat"), 1)

    def test_egg_and_fusion_reservation_block_both_lifecycle_commands(self):
        """The direct equivalent retains #723's current reservation boundary."""
        self.equip()
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(is_egg=True)
        before = self.row()
        self.command("evolve", str(self.mon.pk))
        self.command("hold", "3=")
        self.assertEqual(self.row(), before)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(is_egg=False)
        PlacementService(self.storage).reserve_for_fusion(self.mon)
        before = self.row()
        self.command("evolve", str(self.mon.pk))
        self.command("hold", "3=")
        self.assertEqual(self.row(), before)
        self.assertEqual(self.trainer.get_item_quantity("Metal Coat"), 1)

    def test_battle_lock_rechecked_by_service(self):
        """Both normal command entry and the locked transaction reject battles."""
        self.equip()
        before = self.row()
        self.caller.db.battle_lock = "fixture-battle"
        self.command("evolve", str(self.mon.pk))
        with self.assertRaises(EvolutionError):
            EvolutionService(self.caller).evolve(self.mon)
        self.assertEqual(self.row(), before)

    def test_foreign_owner_is_rejected_at_lookup_and_service(self):
        """Never consume another trainer's held item even with a known UUID."""
        self.equip()
        other = ObjectDB.objects.create(db_key="foreign-" + uuid4().hex)
        trainer = Trainer.objects.create(user=other, trainer_number=Trainer.objects.count() + 1)
        storage = UserStorage.objects.create(user=other)
        self.caller = PlayerView(other, trainer, storage)
        trainer.add_item("Metal Coat", 2)
        before = self.row()
        self.assertIn("No such", self.command("evolve", str(self.mon.pk)))
        with self.assertRaises(EvolutionError):
            EvolutionService(self.caller).evolve(self.mon)
        self.assertEqual(self.row(), before)
        self.assertEqual(trainer.get_item_quantity("Metal Coat"), 2)
        self.assertEqual(self.trainer.get_item_quantity("Metal Coat"), 1)

    def test_conflicting_placement_owner_is_not_repaired_or_transferred(self):
        """An invalid placement must fail closed without silent ownership repair."""
        self.equip()
        other = ObjectDB.objects.create(db_key="placement-owner-" + uuid4().hex)
        storage = UserStorage.objects.create(user=other)
        self.storage.placements.filter(pokemon=self.mon).update(storage=storage)
        before = self.row()
        self.command("evolve", str(self.mon.pk))
        self.assertEqual(self.row(), before)
        self.assertEqual(PokemonPlacement.objects.get(pokemon=self.mon).storage_id, storage.pk)

    def test_failed_save_rolls_back_held_item_receipt_species_and_shared_cache(self):
        """A failure after SQL write still rolls back the entire transition."""
        self.equip()
        before, preserved = self.row(), self.preserved()
        original = OwnedPokemon.save

        def fail_after_save(pokemon, *args, **kwargs):
            """Inject a durable-write failure; never mock a successful effect."""
            original(pokemon, *args, **kwargs)
            raise RuntimeError("fixture failure after save")

        with patch.object(OwnedPokemon, "save", fail_after_save):
            self.assertIn("Evolution failed", self.command("evolve", str(self.mon.pk)))
        self.assertEqual(self.row(), before)
        self.assertEqual(self.preserved(), preserved)
        self.assertEqual((self.mon.species, self.mon.held_item, self.mon.flags),
                         (before["species"], before["held_item"], before["flags"]))
        self.assertIn("evolved into Scizor", self.command("evolve", str(self.mon.pk)))
        self.assertEqual(self.trainer.get_item_quantity("Metal Coat"), 1)

    def test_fresh_locked_state_overrules_stale_cached_item_and_species(self):
        """Unsaved cached values cannot supply or remove evolution permission."""
        self.equip()
        self.mon.species, self.mon.held_item = "Pikachu", "Leftovers"
        self.assertEqual(EvolutionService(self.caller).evolve(self.mon), "Scizor")
        self.assertEqual(self.row()["held_item"], "")

    def test_boxed_evolution_retains_owner_box_position_and_all_mirrors(self):
        """An equipped Pokemon may evolve after a legal deposit without moving."""
        self.equip()
        PlacementService(self.storage).to_box(self.mon)
        before = self.preserved()
        self.assertIn("evolved into Scizor", self.command("evolve", str(self.mon.pk)))
        self.assertEqual(self.preserved(), before)

    def test_porygon_second_stage_needs_explicit_new_request_at_same_level(self):
        """An implicit retry cannot spend the next stage's newly equipped item."""
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(species="Porygon", ability="Trace")
        self.equip("Up-Grade")
        self.command("evolve", str(self.mon.pk))
        self.assertEqual(self.row()["species"], "Porygon2")
        self.equip("Dubious Disc")
        before = self.row()
        self.assertIn("already completed", self.command("evolve", str(self.mon.pk)))
        self.assertEqual(self.row(), before)
        self.assertIn("evolved into Porygon-Z", self.command("evolve", f"{self.mon.pk}=Porygon-Z"))
        self.assertEqual(self.row()["held_item"], "")
        completed = self.row()
        self.command("evolve", f"{self.mon.pk}=Porygon-Z")
        self.assertEqual(self.row(), completed)
        self.assertEqual(self.trainer.get_item_quantity("Dubious Disc"), 1)

    def test_replay_does_not_consume_a_newly_equipped_copy(self):
        """A new held copy after completion survives repeated target requests."""
        self.equip()
        self.command("evolve", f"{self.mon.pk}=Scizor")
        self.equip(copies=1)
        before = self.row()
        self.command("evolve", f"{self.mon.pk}=Scizor")
        self.assertEqual(self.row(), before)
        self.assertEqual(self.row()["held_item"], "Metal Coat")

    def test_legacy_trade_syntax_and_non_item_field_evolutions_are_rejected(self):
        """Direct-transfer syntax is inert; consent trades use their own route."""
        self.equip()
        before = self.row()
        mirrors = self.preserved()
        stock = self.trainer.get_item_quantity("Metal Coat")
        output = self.command("trade", f"{self.mon.pk}=another-player")
        self.assertIn("Use +trade offer", output)
        self.assertIn("require recipient acceptance", output)
        self.assertEqual(self.row(), before)
        self.assertEqual(self.preserved(), mirrors)
        self.assertEqual(self.trainer.get_item_quantity("Metal Coat"), stock)
        for species in ("Kadabra", "Karrablast", "Shelmet"):
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(species=species)
            before = self.row()
            self.command("evolve", str(self.mon.pk))
            self.assertEqual(self.row(), before)

    def race(self, first, second):
        """Start competing requests on independent PostgreSQL connections."""
        barrier = Barrier(2)

        def run(action):
            """Bind one connection per request and release it after completion."""
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

    def test_concurrent_identical_completions_consume_once(self):
        """The storage lock serializes receipt checks and held-item consumption."""
        self.equip()
        before = self.preserved()
        action = lambda: EvolutionService(self.caller).evolve(self.mon, target="Scizor")
        self.assertCountEqual(self.race(action, action), ["Scizor", None])
        self.assertEqual(self.row()["held_item"], "")
        self.assertEqual(self.preserved(), before)
        self.assertEqual(self.trainer.get_item_quantity("Metal Coat"), 1)

    def test_concurrent_remove_and_evolve_conserve_items(self):
        """The held copy is either returned or consumed, never both or lost."""
        self.equip()
        results = self.race(lambda: EvolutionService(self.caller).evolve(self.mon),
                            lambda: EvolutionService(self.caller).hold(3))
        evolved = self.row()["species"] == "Scizor"
        self.assertEqual(self.row()["held_item"], "")
        self.assertEqual(self.trainer.get_item_quantity("Metal Coat"), 1 if evolved else 2)
        self.assertIn("Scizor" if evolved else "rejected", results)

    def test_concurrent_reservation_and_evolve_have_one_legal_order(self):
        """Reservation and evolution share the storage lock; no transfer occurs."""
        self.equip()
        results = self.race(lambda: EvolutionService(self.caller).evolve(self.mon),
                            lambda: PlacementService(self.storage).reserve_for_fusion(self.mon))
        evolved = self.row()["species"] == "Scizor"
        self.assertEqual(self.row()["held_item"], "" if evolved else "Metal Coat")
        self.assertEqual(self.trainer.get_item_quantity("Metal Coat"), 1)
        self.assertEqual(self.row()["trainer_id"], self.trainer.pk)
        self.assertEqual(PokemonPlacement.objects.get(pokemon=self.mon).location_type, "fusion")
        self.assertIn("Scizor" if evolved else "rejected", results)


def mapping_test(source, target, item):
    """Give each reviewed transition an independently reported test result."""
    def test(self):
        """Run the complete discovery/equip/evolve/reload/retry player flow."""
        self.mapping(source, target, item)
    return test


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from evennia.commands.command import Command
        with patch.object(evennia, "Command", Command):
            from commands.player.cmd_account import CmdTradePokemon
            from commands.player.cmd_learn_evolve import CmdEvolvePokemon
            from commands.player.cmd_party import CmdSetHoldItem
            from commands.player.cmd_sheet import CmdSheetPokemon
        from django.db import close_old_connections, connections
        from evennia.objects.models import ObjectDB
        from evennia.utils.ansi import strip_ansi
        from pokemon.data.evolution import lookup_species
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.models.storage import PokemonPlacement, UserStorage
        from pokemon.models.trainer import Trainer
        from pokemon.services.evolution import EvolutionError, EvolutionService
        from pokemon.services.placement import PlacementService
        from pokemon.user import User

        for source, target, item in TradeHeldEvolution.transitions:
            setattr(TradeHeldCases, "test_mapping_" + target.replace("-", "_"), mapping_test(source, target, item))
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(TradeHeldCases))
        print("TRADE_HELD_PLAYER_WALKTHROUGH " + json.dumps(WALKTHROUGH))
        raise SystemExit(not result.wasSuccessful())

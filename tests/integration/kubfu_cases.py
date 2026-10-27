"""Both ordinary Kubfu Scroll purchase/evolution flows on disposable PostgreSQL."""

import json
import re
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
from ui_cases import PlayerView as SessionTransport

WALKTHROUGH = []


class PlayerView(SessionTransport):
    """Adapt session output and delegate ordinary player operations unchanged."""

    def get_pokemon_by_id(self, value):
        """Use the full-ID ownership lookup."""
        return User.get_pokemon_by_id(self, value)

    def get_active_pokemon_by_slot(self, slot):
        """Use canonical party placement for the +use negative control."""
        return User.get_active_pokemon_by_slot(self, slot)

    def add_item(self, name, quantity=1):
        """Acquire actual inventory from the normal shop."""
        return User.add_item(self, name, quantity)

    def spend_money(self, amount):
        """Pay the actual trainer wallet."""
        return User.spend_money(self, amount)


class KubfuCaseBase(unittest.TestCase):
    """Run each branch through the same lifecycle and integrity checks."""

    def setUp(self):
        """Create tagged disposable owner, shop and gapped canonical party."""
        character = ObjectDB.objects.create(db_key="kubfu-owner-" + uuid4().hex)
        self.trainer = Trainer.objects.create(user=character, trainer_number=Trainer.objects.count() + 1, money=50000)
        self.storage = UserStorage.objects.create(user=character)
        self.caller = PlayerView(character, self.trainer, self.storage)
        self.caller.pk = character.pk
        self.room = ObjectDB.objects.create(db_key="kubfu-shop-" + uuid4().hex)
        self.room.db.is_item_shop, self.room.db.store_inventory = True, {}
        self.caller.location = self.room
        self.mon = create_owned_pokemon(
            "Kubfu", self.trainer, 30, ability="Inner Focus", nature="Hardy",
            ivs=[1, 2, 3, 4, 5, 6], evs=[0, 8, 0, 12, 0, 0], held_item="Leftovers",
            active_move_names=["Tackle", "Watergun"],
        )
        PlacementService(self.storage).to_party(self.mon, slot=3)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(
            nickname="Buddy", current_hp=3, status="slp", sleep_turns=2,
            friendship=0, flags=["keep-this-flag"],
        )
        ActiveMoveslot.objects.filter(pokemon=self.mon).update(current_pp=7)
        self.reload()
        for item in (self.item, self.other_item):
            self.trainer.add_item(item, 2)

    def reload(self):
        """Discard the shared model instance and read actual saved state."""
        previous = self.mon
        OwnedPokemon.flush_cached_instance(previous)
        self.mon = OwnedPokemon.objects.get(pk=previous.pk)
        self.assertIsNot(self.mon, previous)

    def row(self):
        """Read fresh SQL scalars, bypassing the identity map."""
        return OwnedPokemon.objects.filter(pk=self.mon.pk).values().get()

    def quantities(self):
        """Keep both item quantities visible for every mutation/rejection."""
        return {item: self.trainer.get_item_quantity(item) for item in (self.item, self.other_item)}

    def command(self, kind, args):
        """Use production parsing and command execution."""
        command = COMMANDS[kind]()
        command.caller, command.args = self.caller, args
        command.parse()
        command.func()
        return self.caller.messages[-1]

    def evolve(self, suffix=None):
        """Submit the complete ID and chosen actual bag item."""
        return self.command("evolve", str(self.mon.pk) + (" " + self.item if suffix is None else suffix))

    def action(self, mon=None, *, item=None, target=None):
        """Use the same locked service for independent-connection races."""
        return EvolutionService(self.caller).evolve(mon or self.mon, item=item or self.item, target=target)

    def preserved(self):
        """Snapshot unrelated scalars, PP, canonical placement and all mirrors."""
        row = self.row()
        for field in ("species", "ability", "flags"):
            row.pop(field)
        return (row, list(ActiveMoveslot.objects.filter(pokemon=self.mon).order_by("slot").values()),
                list(self.storage.placements.filter(pokemon=self.mon).values()),
                list(self.mon.active_slots.values()), list(self.mon.stored_users.values_list("pk", flat=True)),
                list(self.mon.boxes.values_list("pk", flat=True)))

    def unchanged(self, suffix=None):
        """Rejected commands must leave both inventory and actual rows unchanged."""
        before, quantities = self.row(), self.quantities()
        output = self.evolve(suffix)
        self.assertEqual(self.row(), before)
        self.assertEqual(self.quantities(), quantities)
        return output

    def flow(self, level, explicit):
        """Purchase, discover, evolve, reload and retry at both level boundaries."""
        self.mon.set_level(level)
        self.mon.save()
        self.reload()
        self.trainer.remove_item(self.item, 2)
        setup = []
        item_store.node_edit(SimpleNamespace(location=self.room, msg=setup.append), f"add {self.stock_key} 10000 5")
        self.assertIn("Added " + self.stock_key, setup[-1])
        item_store.node_buy(self.caller, self.stock_key + " 2")
        purchase = self.caller.messages[-1]
        self.assertIn("You purchase 2 x " + self.stock_key, purchase)
        self.assertEqual(self.quantities(), {self.item: 2, self.other_item: 2})
        self.assertEqual(Trainer.objects.values_list("money", flat=True).get(pk=self.trainer.pk), 30000)
        self.assertEqual(self.room.db.store_inventory[self.stock_key]["quantity"], 3)
        inventory = self.command("inventory", "")
        self.assertIn(self.item + " x2", inventory)
        self.assertIn("Evolution Items", format_inventory_by_category(gather_inventory_pairs(self.caller)))
        detail = self.command("itemdex", self.item)
        self.assertIn(self.target, detail)
        self.assertIn("Category: Evolution Items", detail)
        self.assertIn("Reference price: $10000", detail)
        sheet = self.command("party", "3")
        identifier = re.search(r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", strip_ansi(sheet))
        self.assertIsNotNone(identifier)
        self.assertEqual(identifier.group(), str(self.mon.pk))
        self.caller.location = None  # No tower, region, time or environment is required.
        before, maximum = self.preserved(), get_max_hp(self.mon)
        suffix = " " + self.item + ("=" + self.target if explicit else "")
        output = self.evolve(suffix)
        self.assertIn("evolved into " + self.target, output)
        self.assertEqual(self.row()["species"], self.target)
        self.assertEqual(self.row()["ability"], "Unseen Fist")
        self.assertEqual(self.preserved(), before)
        self.assertEqual(self.quantities(), {self.item: 1, self.other_item: 2})
        self.assertIn("keep-this-flag", self.row()["flags"])
        self.assertEqual(len([flag for flag in self.row()["flags"] if flag.startswith("evo:")]), 1)
        self.reload()
        self.assertEqual(self.mon.species, self.target)
        self.assertEqual(list(self.mon.types), self.expected_types)
        result = self.command("party", "3")
        for text in (self.target, "Leftovers", str(self.mon.pk)):
            self.assertIn(text, result)
        self.assertIn("already completed", self.unchanged(suffix))
        self.unchanged(" " + self.other_item + "=" + self.other_target)
        WALKTHROUGH.append({"item": self.item, "target": self.target, "level": level, "explicit_target": explicit,
                            "id": str(self.mon.pk), "commands": ["shop Buy: " + self.stock_key + " 2", "+inventory",
                            "+itemdex " + self.item, "+party 3", "+evolve " + str(self.mon.pk) + suffix,
                            "SQL reload", "+party 3", "retry same evolution", "reject other-style Scroll"],
                            "purchase_output": purchase, "evolution_output": output, "bag_after": self.quantities(),
                            "ability_after": self.row()["ability"], "types_after": list(self.mon.types),
                            "hp_after": self.row()["current_hp"], "max_hp_before": maximum,
                            "max_hp_after": get_max_hp(self.mon), "held_after": self.row()["held_item"],
                            "same_identity_and_saved_state": True, "SQL_reload_and_retry": True})

    def test_flow_level_one_implicit(self):
        """A real bag Scroll is sufficient even at level one and friendship zero."""
        self.flow(1, False)

    def test_flow_level_one_hundred_explicit(self):
        """An exact optional target agrees with the item at the upper boundary."""
        self.flow(100, True)

    def test_missing_argument_item_or_target_only_cannot_evolve(self):
        """Neither bag stock nor a named branch supplies a missing trigger."""
        self.unchanged("")
        self.unchanged("=" + self.target)
        self.trainer.remove_item(self.item, 2)
        self.assertIn("do not have", self.unchanged())

    def test_held_only_copy_does_not_activate_and_returns_normally(self):
        """Holding a Scroll is reversible and distinct from the bag debit."""
        self.command("hold", "3=" + self.item)
        self.trainer.remove_item(self.item)
        self.unchanged("")
        self.unchanged()
        self.assertEqual(self.row()["held_item"], self.item)
        self.assertEqual(self.quantities()[self.item], 0)
        self.command("hold", "3=")
        self.assertEqual(self.quantities()[self.item], 1)

    def test_bag_use_preserves_a_separate_held_copy(self):
        """A successful bag debit does not consume the equipped object."""
        self.command("hold", "3=" + self.item)
        self.assertIn("evolved into " + self.target, self.evolve())
        self.assertEqual(self.row()["held_item"], self.item)
        self.assertEqual(self.quantities(), {self.item: 0, self.other_item: 2})

    def test_plot_flags_and_tower_prose_do_not_supply_permission(self):
        """Arbitrary completion text/flags cannot replace the chosen bag item."""
        self.room.db.tower_complete = self.caller.db.tower_complete = True
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(flags=["tower:single", "tower:rapid", "tower_complete"])
        self.unchanged("")
        self.unchanged(" Defeat the Single Strike Tower")
        self.unchanged("=" + self.target)

    def test_everstone_blocks(self):
        """The selected exception retains the shared held-item guard."""
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(held_item="Everstone")
        self.unchanged()

    def test_eggs_are_rejected(self):
        """Eggs cannot use a functional Scroll."""
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(is_egg=True)
        self.unchanged()

    def test_fusion_reservation_is_rejected(self):
        """Existing reservations remain authoritative."""
        PlacementService(self.storage).reserve_for_fusion(self.mon)
        self.unchanged()

    def test_battle_lock_is_rechecked(self):
        """Command and locked service both reject field evolution during battle."""
        self.caller.db.battle_lock = "kubfu-fixture-battle"
        self.unchanged()
        with self.assertRaises(EvolutionError):
            self.action()

    def test_foreign_owner_is_rejected(self):
        """A known UUID cannot cross actual trainer/storage ownership."""
        other = ObjectDB.objects.create(db_key="kubfu-foreign-" + uuid4().hex)
        trainer = Trainer.objects.create(user=other, trainer_number=Trainer.objects.count() + 1)
        self.caller = PlayerView(other, trainer, UserStorage.objects.create(user=other))
        self.caller.pk, self.caller.location = other.pk, self.room
        trainer.add_item(self.item, 2)
        self.assertIn("No such", self.unchanged())
        with self.assertRaises(EvolutionError):
            self.action()
        self.assertEqual(trainer.get_item_quantity(self.item), 2)

    def test_conflicting_canonical_owner_is_not_repaired(self):
        """Invalid placement fails closed without moving the Pokemon."""
        other = ObjectDB.objects.create(db_key="kubfu-conflict-" + uuid4().hex)
        storage = UserStorage.objects.create(user=other)
        self.storage.placements.filter(pokemon=self.mon).update(storage=storage)
        self.unchanged()
        self.assertEqual(PokemonPlacement.objects.get(pokemon=self.mon).storage_id, storage.pk)

    def test_mismatched_partial_unknown_and_gmax_targets_are_rejected(self):
        """Exact target selection never crosses styles or enables battle forms."""
        for target in (self.other_target, "Urshifu-Single-Strike", "Urshifu-Rapid", "Urshifu-Gmax",
                       "Urshifu-Rapid-Strike-Gmax", "unknown", ""):
            self.unchanged(" " + self.item + "=" + target)

    def test_wrong_species_and_nickname_spoofing_are_rejected(self):
        """Actual native species, not display names, drives eligibility."""
        for species in ("Pikachu", "Urshifu", "Urshifu-Rapid-Strike", "Urshifu-Gmax", "Bisharp", "Ursaring"):
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(species=species, nickname="Kubfu")
            self.unchanged()

    def test_partial_or_unrelated_item_names_are_rejected(self):
        """Complete Scroll names cannot be replaced by prefixes or another item."""
        for item in ("Scroll", "Darkness", "Waters", "Scroll of Water", "Peat Block", "Water Stone"):
            self.unchanged(" " + item)

    def test_unreviewed_condition_cannot_inherit_the_exception(self):
        """A future changed rule requires review before its bag item works."""
        with patch.dict(lookup_species(self.target).raw, evoCondition="unreviewed tower condition"):
            self.unchanged()

    def test_failed_save_rolls_back_items_species_receipt_and_cache(self):
        """A failure after actual SQL save must undo every transition write."""
        before, preserved = self.row(), self.preserved()
        original = OwnedPokemon.save

        def fail_after_save(mon, *args, **kwargs):
            original(mon, *args, **kwargs)
            raise RuntimeError("kubfu fixture failure after actual SQL save")

        with patch.object(OwnedPokemon, "save", fail_after_save):
            self.assertIn("Evolution failed", self.evolve())
        self.assertEqual(self.row(), before)
        self.assertEqual(self.preserved(), preserved)
        self.assertEqual((self.mon.species, self.mon.flags), (before["species"], before["flags"]))
        self.assertEqual(self.quantities(), {self.item: 2, self.other_item: 2})
        self.assertIn("evolved into " + self.target, self.evolve())

    def test_failed_debit_after_sql_rolls_back_without_transition(self):
        """Inventory SQL failure cannot consume a Scroll or publish an evolution."""
        original = Trainer.remove_item

        def fail_after_debit(trainer, *args, **kwargs):
            original(trainer, *args, **kwargs)
            raise RuntimeError("kubfu fixture failure after actual debit")

        with patch.object(Trainer, "remove_item", fail_after_debit):
            self.unchanged()
        self.assertIn("evolved into " + self.target, self.evolve())

    def test_fresh_sql_source_overrules_unsaved_cached_values(self):
        """Stale shared instances cannot manufacture or suppress eligibility."""
        self.mon.species, self.mon.held_item = "Pikachu", "Everstone"
        self.assertEqual(self.action(), self.target)
        self.assertEqual(self.row()["held_item"], "Leftovers")

    def test_boxed_evolution_preserves_placement_and_mirrors(self):
        """Canonical boxes use the same atomic service and keep the same UUID."""
        PlacementService(self.storage).to_box(self.mon)
        before = self.preserved()
        self.assertIn("evolved into " + self.target, self.evolve())
        self.assertEqual(self.preserved(), before)

    def test_legacy_complete_name_aliases_debit_one_total(self):
        """Old complete spellings represent real stock, without creating copies."""
        self.trainer.remove_item(self.item, 2)
        InventoryEntry.objects.create(owner=self.trainer, item_name=self.item, quantity=1)
        InventoryEntry.objects.create(owner=self.trainer, item_name=self.item.replace(" ", "-"), quantity=2)
        self.assertEqual(self.quantities()[self.item], 3)
        self.evolve()
        self.assertEqual(self.quantities()[self.item], 2)

    def test_replay_reload_and_other_style_request_do_not_spend_again(self):
        """Repeated completion is a no-op and cannot transform an evolved form."""
        self.evolve(" " + self.item + "=" + self.target)
        self.reload()
        self.assertIn("already completed", self.unchanged(" " + self.item.lower() + "=" + self.target.lower()))
        self.unchanged()
        self.unchanged(" " + self.other_item + "=" + self.other_target)

    def test_use_does_not_invent_a_second_route(self):
        """Field +use rejects the Scroll without consuming anything."""
        before, quantities = self.row(), self.quantities()
        self.assertIn("not usable", self.command("use", self.item + "=3"))
        self.assertEqual(self.row(), before)
        self.assertEqual(self.quantities(), quantities)

    def race(self, first, second):
        """Run competing requests on independent real PG connections."""
        barrier = Barrier(2)

        def run(action):
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

    def test_concurrent_identical_completion_debits_once(self):
        """The storage lock and receipt serialize repeated exact requests."""
        action = lambda: self.action(target=self.target)
        self.assertCountEqual(self.race(action, action), [self.target, None])
        self.assertEqual(self.quantities(), {self.item: 1, self.other_item: 2})

    def test_concurrent_opposite_styles_choose_one_without_double_debit(self):
        """Two valid competing Scrolls cannot evolve or switch the same ID twice."""
        result = self.race(self.action, lambda: self.action(item=self.other_item, target=self.other_target))
        self.assertEqual(result.count("rejected"), 1)
        species = self.row()["species"]
        self.assertIn(species, (self.target, self.other_target))
        self.assertIn(species, result)
        self.assertEqual(self.quantities(), {self.item: 1 if species == self.target else 2,
                                            self.other_item: 1 if species == self.other_target else 2})

    def test_concurrent_pokemon_compete_for_one_copy(self):
        """A last bag copy cannot evolve two separately owned Kubfu."""
        other = create_owned_pokemon("Kubfu", self.trainer, 30, ivs=[0] * 6, evs=[0] * 6)
        self.trainer.remove_item(self.item)
        self.assertCountEqual(self.race(self.action, lambda: self.action(other)), [self.target, "rejected"])
        self.assertEqual(self.quantities()[self.item], 0)
        self.assertEqual(OwnedPokemon.objects.filter(trainer=self.trainer, species=self.target).count(), 1)

    def test_concurrent_reservation_has_one_legal_order(self):
        """Fusion cannot reserve first and still permit a later evolution."""
        self.race(self.action, lambda: PlacementService(self.storage).reserve_for_fusion(self.mon))
        evolved = self.row()["species"] == self.target
        self.assertEqual(self.quantities()[self.item], 1 if evolved else 2)
        self.assertEqual(PokemonPlacement.objects.get(pokemon=self.mon).location_type, "fusion")

    def test_concurrent_deposit_preserves_same_evolved_id(self):
        """The common storage lock serializes box placement and evolution."""
        self.race(self.action, lambda: PlacementService(self.storage).to_box(self.mon))
        self.assertEqual(self.row()["species"], self.target)
        self.assertEqual(self.quantities()[self.item], 1)
        placement = PokemonPlacement.objects.get(pokemon=self.mon)
        self.assertEqual((placement.location_type, placement.storage_id), ("box", self.storage.pk))


class DarknessCases(KubfuCaseBase):
    """Single Strike functional Scroll coverage."""

    item, target, stock_key = "Scroll of Darkness", "Urshifu", "ScrollOfDarkness"
    other_item, other_target = "Scroll of Waters", "Urshifu-Rapid-Strike"
    expected_types = ["Fighting", "Dark"]


class WatersCases(KubfuCaseBase):
    """Rapid Strike functional Scroll coverage."""

    item, target, stock_key = "Scroll of Waters", "Urshifu-Rapid-Strike", "ScrollOfWaters"
    other_item, other_target = "Scroll of Darkness", "Urshifu"
    expected_types = ["Fighting", "Water"]


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from evennia.commands.command import Command
        with patch.object(evennia, "Command", Command):
            from commands.player.cmd_inventory import CmdInventory, CmdUseItem
            from commands.player.cmd_learn_evolve import CmdEvolvePokemon
            from commands.player.cmd_party import CmdSetHoldItem
            from commands.player.cmd_pokedex import CmdItemdexSearch
            from commands.player.cmd_sheet import CmdSheetPokemon
        from django.db import close_old_connections, connections
        from evennia.objects.models import ObjectDB
        from evennia.utils.ansi import strip_ansi
        from menus import item_store
        from pokemon.data.evolution import lookup_species
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon, get_max_hp
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.models.storage import PokemonPlacement, UserStorage
        from pokemon.models.trainer import InventoryEntry, Trainer
        from pokemon.services.evolution import EvolutionError, EvolutionService
        from pokemon.services.placement import PlacementService
        from pokemon.user import User
        from utils.inventory_view import format_inventory_by_category, gather_inventory_pairs

        COMMANDS = {"evolve": CmdEvolvePokemon, "hold": CmdSetHoldItem, "inventory": CmdInventory,
                    "itemdex": CmdItemdexSearch, "party": CmdSheetPokemon, "use": CmdUseItem}
        suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls)
                                   for cls in (DarknessCases, WatersCases))
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        print("KUBFU_PLAYER_WALKTHROUGH " + json.dumps(WALKTHROUGH))
        raise SystemExit(not result.wasSuccessful())

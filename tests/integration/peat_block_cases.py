"""Real shop/command/model Peat Block flows on explicitly disposable PostgreSQL.

Session output is captured; ownership, inventory, rules, transactions and SQL
are real. The harness refuses fallback game connections and runs no migrations.
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
from ui_cases import PlayerView as SessionTransport

WALKTHROUGH = []


class PlayerView(SessionTransport):
    """Adapt only transport and delegate player operations to production code."""

    def get_pokemon_by_id(self, value):
        """Use the complete-ID ownership lookup shipped with the player."""
        return User.get_pokemon_by_id(self, value)

    def get_active_pokemon_by_slot(self, slot):
        """Expose the normal canonical party-slot lookup for the +use control."""
        return User.get_active_pokemon_by_slot(self, slot)

    def add_item(self, name, quantity=1):
        """Use normal inventory acquisition for shop purchases."""
        return User.add_item(self, name, quantity)

    def spend_money(self, amount):
        """Use normal player currency mutation for purchases."""
        return User.spend_money(self, amount)


class PeatBlockCases(unittest.TestCase):
    """Prove the bounded equivalent and unchanged shared lifecycle guarantees."""

    def setUp(self):
        """Create one ordinary owner and a gapped canonical party fixture."""
        character = ObjectDB.objects.create(db_key="peat-owner-" + uuid4().hex)
        self.trainer = Trainer.objects.create(
            user=character, trainer_number=Trainer.objects.count() + 1, money=50000,
        )
        self.storage = UserStorage.objects.create(user=character)
        self.caller = PlayerView(character, self.trainer, self.storage)
        self.caller.pk = character.pk
        self.room = ObjectDB.objects.create(db_key="peat-shop-" + uuid4().hex)
        self.room.db.is_item_shop = True
        self.room.db.store_inventory = {}
        self.caller.location = self.room
        self.mon = create_owned_pokemon(
            "Ursaring", self.trainer, 30, ability="Guts", nature="Hardy",
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
        self.trainer.add_item("Peat Block", 2)

    def reload(self):
        """Discard the shared model instance and force a new SQL-backed read."""
        previous = self.mon
        OwnedPokemon.flush_cached_instance(previous)
        self.mon = OwnedPokemon.objects.get(pk=previous.pk)
        self.assertIsNot(self.mon, previous)

    def row(self):
        """Read actual persisted scalars without the identity map."""
        return OwnedPokemon.objects.filter(pk=self.mon.pk).values().get()

    def quantity(self):
        """Read authoritative normalized inventory quantities."""
        return self.trainer.get_item_quantity("Peat Block")

    def command(self, kind, args):
        """Run shipped ordinary command parsing and execution."""
        command = COMMANDS[kind]()
        command.caller, command.args = self.caller, args
        command.parse()
        command.func()
        return self.caller.messages[-1]

    def evolve(self, suffix=" Peat Block"):
        """Submit the normal complete-ID evolution request."""
        return self.command("evolve", str(self.mon.pk) + suffix)

    def action(self, mon=None, target=None):
        """Invoke the same locked service for concurrent requests."""
        return EvolutionService(self.caller).evolve(
            mon or self.mon, item="Peat Block", target=target,
        )

    def preserved(self):
        """Snapshot all unrelated scalars, PP, placement and compatibility mirrors."""
        row = self.row()
        for key in ("species", "ability", "type_", "flags"):
            row.pop(key, None)
        return (
            row, list(ActiveMoveslot.objects.filter(pokemon=self.mon).order_by("slot").values()),
            list(self.storage.placements.filter(pokemon=self.mon).values()),
            list(self.mon.active_slots.values()),
            list(self.mon.stored_users.values_list("pk", flat=True)),
            list(self.mon.boxes.values_list("pk", flat=True)),
        )

    def unchanged(self, suffix=" Peat Block"):
        """A rejected ordinary command must change neither rows nor inventory."""
        before, quantity = self.row(), self.quantity()
        output = self.evolve(suffix)
        self.assertEqual(self.row(), before)
        self.assertEqual(self.quantity(), quantity)
        return output

    def flow(self, ability, context):
        """Buy, inspect, discover ID, evolve, reload and retry with real state."""
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(ability=ability)
        self.reload()
        self.trainer.remove_item("Peat Block", 2)
        setup_messages = []
        fixture = SimpleNamespace(location=self.room, msg=setup_messages.append)
        item_store.node_edit(fixture, "add PeatBlock 10000 5")
        self.assertIn("Added PeatBlock.", setup_messages[-1])
        item_store.node_buy(self.caller, "PeatBlock 2")
        purchase = self.caller.messages[-1]
        self.assertIn("You purchase 2 x PeatBlock", purchase)
        self.assertEqual(self.quantity(), 2)
        self.assertEqual(Trainer.objects.get(pk=self.trainer.pk).money, 30000)
        self.assertEqual(self.room.db.store_inventory["PeatBlock"]["quantity"], 3)
        self.assertIn("Peat Block x2", self.command("inventory", ""))
        categories = format_inventory_by_category(gather_inventory_pairs(self.caller))
        self.assertIn("Evolution Items", categories)
        detail = self.command("itemdex", "Peat Block")
        self.assertIn("+evolve", detail)
        self.assertIn("Category: Evolution Items", detail)
        self.assertIn("Reference price: $10000", detail)
        sheet = self.command("party", "3")
        identifier = re.search(r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", strip_ansi(sheet))
        self.assertIsNotNone(identifier)
        self.assertEqual(identifier.group(), str(self.mon.pk))
        if context == "missing_room":
            self.caller.location = None
        else:
            self.room.db.time_of_day = context
        before = self.preserved()
        maximum_before = get_max_hp(self.mon)
        suffix = " Peat Block=Ursaluna" if context == "night" else " Peat Block"
        output = self.evolve(suffix)
        self.assertIn("evolved into Ursaluna", output)
        self.assertEqual(self.row()["species"], "Ursaluna")
        slot = {"Guts": "0", "Quick Feet": "1", "Unnerve": "H"}[ability]
        self.assertEqual(self.row()["ability"], lookup_species("Ursaluna").raw["abilities"][slot])
        self.assertEqual(self.quantity(), 1)
        self.assertEqual(self.preserved(), before)
        self.assertIn("keep-this-flag", self.row()["flags"])
        self.assertEqual(len([flag for flag in self.row()["flags"] if flag.startswith("evo:")]), 1)
        self.reload()
        self.assertEqual(self.mon.species, "Ursaluna")
        self.assertEqual(list(self.mon.types), ["Ground", "Normal"])
        result_sheet = self.command("party", "3")
        self.assertIn("Ursaluna", result_sheet)
        self.assertIn("Leftovers", result_sheet)
        self.assertIn(str(self.mon.pk), result_sheet)
        self.assertEqual(Trainer.objects.get(pk=self.trainer.pk).money, 30000)
        self.assertIn("already completed", self.unchanged(suffix))
        WALKTHROUGH.append({
            "ability_before": ability, "ability_after": self.row()["ability"],
            "context": context, "item": "Peat Block", "bag_after": 1,
            "commands": ["shop Buy: PeatBlock 2", "+inventory", "+itemdex Peat Block",
                         "+party 3", "+evolve " + identifier.group() + suffix, "+party 3"],
            "purchase_output": purchase, "evolve_output": output,
            "species_after": self.row()["species"], "id": identifier.group(),
            "hp_after": self.row()["current_hp"], "max_hp_before": maximum_before,
            "max_hp_after": get_max_hp(self.mon), "held_after": self.row()["held_item"],
            "other_state_preserved": True, "SQL_reload_and_retry": True,
        })

    def test_no_explicit_bag_argument_or_missing_bag_cannot_evolve(self):
        """Missing input does not default to this item, even with bag stock."""
        self.unchanged("")
        self.trainer.remove_item("Peat Block", 2)
        self.assertIn("do not have", self.unchanged())

    def test_held_only_copy_does_not_activate_and_returns_normally(self):
        """Generic +hold is reversible and cannot supply the required bag item."""
        self.command("hold", "3=Peat Block")
        self.trainer.remove_item("Peat Block")
        self.assertEqual(self.quantity(), 0)
        self.unchanged("")
        self.unchanged()
        self.assertEqual(self.row()["held_item"], "Peat Block")
        self.command("hold", "3=")
        self.assertEqual(self.quantity(), 1)

    def test_bag_use_preserves_an_equipped_copy(self):
        """Only the actual bag debit belongs to this transition."""
        self.command("hold", "3=Peat Block")
        self.assertIn("evolved into Ursaluna", self.evolve())
        self.assertEqual(self.row()["held_item"], "Peat Block")
        self.assertEqual(self.quantity(), 0)

    def test_moon_flags_and_text_cannot_replace_missing_item(self):
        """Neither client prose nor arbitrary attributes create lunar permission."""
        self.room.db.full_moon, self.room.db.moon_phase = True, "full"
        self.caller.db.full_moon = True
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(flags=["full_moon", "moon:full"])
        self.unchanged("")
        self.unchanged(" full moon")
        self.unchanged(" Peat Block full moon")
        self.trainer.remove_item("Peat Block", 2)
        self.unchanged()

    def test_everstone_blocks_real_bag_use(self):
        """The exception retains the shared Everstone gate."""
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(held_item="Everstone")
        self.unchanged()

    def test_eggs_are_rejected(self):
        """Eggs cannot activate the item."""
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(is_egg=True)
        self.unchanged()

    def test_fusion_reservations_are_rejected(self):
        """The rule cannot mutate a Pokemon reserved outside party/box storage."""
        PlacementService(self.storage).reserve_for_fusion(self.mon)
        self.unchanged()

    def test_battle_lock_rechecked_by_locked_service(self):
        """Command and service both reject field evolution during a battle."""
        self.caller.db.battle_lock = "peat-fixture-battle"
        self.unchanged()
        with self.assertRaises(EvolutionError):
            self.action()

    def test_foreign_owner_rejected_by_lookup_and_service(self):
        """Knowing the UUID never authorizes another trainer's evolution."""
        other = ObjectDB.objects.create(db_key="peat-foreign-" + uuid4().hex)
        trainer = Trainer.objects.create(user=other, trainer_number=Trainer.objects.count() + 1)
        storage = UserStorage.objects.create(user=other)
        self.caller = PlayerView(other, trainer, storage)
        self.caller.pk, self.caller.location = other.pk, self.room
        trainer.add_item("Peat Block", 2)
        self.assertIn("No such", self.unchanged())
        with self.assertRaises(EvolutionError):
            self.action()
        self.assertEqual(trainer.get_item_quantity("Peat Block"), 2)

    def test_conflicting_canonical_owner_is_not_repaired(self):
        """Invalid storage ownership fails closed without moving the Pokemon."""
        other = ObjectDB.objects.create(db_key="peat-conflict-" + uuid4().hex)
        storage = UserStorage.objects.create(user=other)
        self.storage.placements.filter(pokemon=self.mon).update(storage=storage)
        self.unchanged()
        self.assertEqual(PokemonPlacement.objects.get(pokemon=self.mon).storage_id, storage.pk)

    def test_bloodmoon_target_never_selects_or_transforms(self):
        """Both source-to-Bloodmoon and normal-to-Bloodmoon are unavailable."""
        self.unchanged(" Peat Block=Ursaluna-Bloodmoon")
        self.evolve()
        self.unchanged(" Peat Block=Ursaluna-Bloodmoon")
        self.assertEqual(self.row()["species"], "Ursaluna")

    def test_wrong_species_and_unrelated_other_rules_consume_nothing(self):
        """The item cannot skip stages, use nicknames or bypass other conditions."""
        for species in ("Teddiursa", "Pikachu", "Inkay", "Primeape", "Bisharp", "Kubfu", "Stantler"):
            with self.subTest(species=species):
                OwnedPokemon.objects.filter(pk=self.mon.pk).update(species=species, nickname="Ursaring")
                self.unchanged()

    def test_partial_items_and_targets_remain_invalid(self):
        """Only complete identities are accepted by the normal parser/rules."""
        for suffix in (" Peat", " Block", " Moon Stone", " Peat Block=Ursal"):
            self.unchanged(suffix)

    def test_changed_rule_metadata_fails_without_consumption(self):
        """Future unknown predicates require review instead of inheriting access."""
        with patch.dict(lookup_species("Ursaluna").raw, evoCondition="unreviewed full moon"):
            self.unchanged()

    def test_failed_save_rolls_back_bag_species_receipt_and_shared_cache(self):
        """A failure after actual SQL save undoes every write and permits retry."""
        before, preserved = self.row(), self.preserved()
        original = OwnedPokemon.save

        def fail_after_save(mon, *args, **kwargs):
            """Inject an actual post-write failure, never a successful effect."""
            original(mon, *args, **kwargs)
            raise RuntimeError("peat fixture failure after SQL save")

        with patch.object(OwnedPokemon, "save", fail_after_save):
            self.assertIn("Evolution failed", self.evolve())
        self.assertEqual(self.row(), before)
        self.assertEqual(self.preserved(), preserved)
        self.assertEqual((self.mon.species, self.mon.flags), (before["species"], before["flags"]))
        self.assertEqual(self.quantity(), 2)
        self.assertIn("evolved into Ursaluna", self.evolve())
        self.assertEqual(self.quantity(), 1)

    def test_failed_debit_writes_no_species_or_receipt(self):
        """A denied real inventory debit never partially applies the effect."""
        with patch.object(Trainer, "remove_item", return_value=False):
            self.unchanged()

    def test_fresh_locked_source_overrules_unsaved_cached_values(self):
        """Unsaved cached values cannot create or destroy source eligibility."""
        self.mon.species, self.mon.held_item = "Pikachu", "Everstone"
        self.assertEqual(self.action(), "Ursaluna")
        self.assertEqual(self.row()["held_item"], "Leftovers")

    def test_boxed_evolution_keeps_owner_box_and_mirrors(self):
        """Legal stored evolution uses the same lifecycle service and placement."""
        PlacementService(self.storage).to_box(self.mon)
        before = self.preserved()
        self.assertIn("evolved into Ursaluna", self.evolve())
        self.assertEqual(self.preserved(), before)

    def test_legacy_inventory_aliases_debit_exactly_one_total(self):
        """Old complete-name spellings are real inventory, not new free copies."""
        self.trainer.remove_item("Peat Block", 2)
        InventoryEntry.objects.create(owner=self.trainer, item_name="Peat Block", quantity=1)
        InventoryEntry.objects.create(owner=self.trainer, item_name="peat-block", quantity=2)
        self.assertEqual(self.quantity(), 3)
        self.evolve()
        self.assertEqual(self.row()["species"], "Ursaluna")
        self.assertEqual(self.quantity(), 2)

    def test_replay_and_different_target_request_do_not_debit_again(self):
        """Same receipts replay; a different invalid request consumes nothing."""
        self.evolve(" Peat Block=Ursaluna")
        self.reload()
        self.assertIn("already completed", self.unchanged(" peat-block=ursaluna"))
        self.unchanged()

    def test_use_does_not_invent_a_second_evolution_route(self):
        """The supported bag interface is +evolve; +use does not consume it."""
        before = self.row()
        self.assertIn("not usable", self.command("use", "Peat Block=3"))
        self.assertEqual(self.row(), before)
        self.assertEqual(self.quantity(), 2)

    def race(self, first, second):
        """Use independent PG connections and synchronize both requests."""
        barrier = Barrier(2)

        def run(action):
            """Keep each worker's real transaction isolated from other connections."""
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

    def test_concurrent_identical_completions_debit_once(self):
        """The storage lock and receipt serialize duplicate requests."""
        action = lambda: self.action(target="Ursaluna")
        self.assertCountEqual(self.race(action, action), ["Ursaluna", None])
        self.assertEqual(self.quantity(), 1)

    def test_concurrent_distinct_requests_cannot_debit_twice(self):
        """Implicit/explicit targets still produce only one transition."""
        self.assertCountEqual(self.race(self.action, lambda: self.action(target="Ursaluna")),
                              ["Ursaluna", "rejected"])
        self.assertEqual(self.quantity(), 1)

    def test_concurrent_pokemon_compete_for_the_last_bag_copy(self):
        """One item cannot evolve two different eligible owned Pokemon."""
        other = create_owned_pokemon("Ursaring", self.trainer, 30, nature="Hardy",
                                     ivs=[0] * 6, evs=[0] * 6, active_move_names=["Tackle"])
        self.trainer.remove_item("Peat Block")
        self.assertCountEqual(self.race(self.action, lambda: self.action(other)),
                              ["Ursaluna", "rejected"])
        self.assertEqual(self.quantity(), 0)
        self.assertEqual(OwnedPokemon.objects.filter(trainer=self.trainer, species="Ursaluna").count(), 1)

    def test_concurrent_reservation_has_one_legal_serial_order(self):
        """Fusion reservation never permits a later unauthorized transition."""
        result = self.race(self.action, lambda: PlacementService(self.storage).reserve_for_fusion(self.mon))
        evolved = self.row()["species"] == "Ursaluna"
        self.assertIn("Ursaluna" if evolved else "rejected", result)
        self.assertEqual(self.quantity(), 1 if evolved else 2)
        self.assertEqual(PokemonPlacement.objects.get(pokemon=self.mon).location_type, "fusion")

    def test_concurrent_deposit_keeps_same_evolved_identity(self):
        """Shared storage locking permits evolution/deposit without moving owners."""
        self.race(self.action, lambda: PlacementService(self.storage).to_box(self.mon))
        self.assertEqual(self.row()["species"], "Ursaluna")
        self.assertEqual(self.quantity(), 1)
        placement = PokemonPlacement.objects.get(pokemon=self.mon)
        self.assertEqual((placement.location_type, placement.storage_id), ("box", self.storage.pk))


def flow_test(ability, context):
    """Report each ability/context walkthrough independently."""
    def test(self):
        """Exercise the complete ordinary purchase/evolution/reload flow."""
        self.flow(ability, context)
    return test


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

        COMMANDS = {"evolve": CmdEvolvePokemon, "hold": CmdSetHoldItem,
                    "inventory": CmdInventory, "itemdex": CmdItemdexSearch,
                    "party": CmdSheetPokemon, "use": CmdUseItem}
        for ability, context in (("Guts", "missing_room"), ("Quick Feet", "day"), ("Unnerve", "night")):
            setattr(PeatBlockCases, "test_flow_" + context, flow_test(ability, context))
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PeatBlockCases))
        print("PEAT_BLOCK_PLAYER_WALKTHROUGH " + json.dumps(WALKTHROUGH))
        raise SystemExit(not result.wasSuccessful())

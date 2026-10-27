"""Real shop-to-+use recovery flows and atomic party revival in isolated PG.

Requires an explicit PF2_TEST_POSTGRES_DSN. Session transport is captured;
commands, purchase/inventory operations, medicine effects and models are real.
"""

import json
import re
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
from pokemon.items import FIELD_RECOVERY_ITEMS

WALKTHROUGH = []


class PlayerView:
    """Bind real player ownership/attributes and only adapt session transport."""

    def __init__(self, character, trainer, storage, room):
        """Use no staff permissions or live game session."""
        self.pk = self.id = character.pk
        self.key = self.name = character.key
        self.db, self.ndb = character.db, character.ndb
        self.attributes = character.attributes
        self.trainer, self.storage, self.location = trainer, storage, room
        self.messages = []

    def msg(self, text, **kwargs):
        """Record the command result as an ordinary client would receive it."""
        self.messages.append(str(text))

    def add_item(self, name, quantity=1):
        """Delegate acquisition to the production player's inventory method."""
        return User.add_item(self, name, quantity)

    def spend_money(self, amount):
        """Delegate purchase currency to the production player's method."""
        return User.spend_money(self, amount)


class FoodCases(unittest.TestCase):
    """Verify all definitions and relevant fresh-state/transaction boundaries."""

    def setUp(self):
        """Create a tagged disposable character, shop and gapped canonical party."""
        self.character = ObjectDB.objects.create(db_key="field-food-" + uuid4().hex)
        self.trainer = Trainer.objects.create(user=self.character, trainer_number=Trainer.objects.count() + 1,
                                              money=200000)
        self.storage = UserStorage.objects.create(user=self.character)
        self.room = ObjectDB.objects.create(db_key="fixture-shop-" + uuid4().hex)
        self.room.db.is_item_shop = True
        self.room.db.store_inventory = {}
        self.mon = self.create_mon(3)
        self.maximum = get_max_hp(self.mon)
        self.caller = PlayerView(self.character, self.trainer, self.storage, self.room)

    def create_mon(self, slot):
        """Use the production factory and explicit canonical slots for fixtures."""
        mon = create_owned_pokemon("Mew", self.trainer, 50, nature="Hardy", ivs=[0] * 6,
                                   evs=[0, 8, 0, 12, 0, 0], active_move_names=["Tackle", "Watergun"])
        PlacementService(self.storage).to_party(mon, slot=slot)
        OwnedPokemon.objects.filter(pk=mon.pk).update(nickname="Food Test", current_hp=1, status="slp",
                                                      sleep_turns=2, friendship=137, flags=["keep-this-flag"],
                                                      held_item="Leftovers")
        ActiveMoveslot.objects.filter(pokemon=mon).update(current_pp=7)
        OwnedPokemon.flush_cached_instance(mon)
        return OwnedPokemon.objects.get(pk=mon.pk)

    def row(self, mon=None):
        """Read actual SQL values instead of Evennia's identity-map instance."""
        return OwnedPokemon.objects.filter(pk=(mon or self.mon).pk).values().get()

    def state(self, mon=None, **fields):
        """Keep direct fixture setup separate from the ordinary-player flow."""
        OwnedPokemon.objects.filter(pk=(mon or self.mon).pk).update(**fields)

    def command(self, args, kind="use"):
        """Run normal parsing and execution of production player commands."""
        command = {"use": CmdUseItem, "inventory": CmdInventory,
                   "itemdex": CmdItemdexSearch, "party": CmdSheetPokemon}[kind]()
        command.caller, command.args = self.caller, args
        command.parse()
        command.func()
        return self.caller.messages[-1]

    def give(self, item, count=2):
        """Give negative fixtures real inventory without invoking staff commands."""
        self.trainer.add_item(item, count)

    def preserved(self, *mons):
        """Capture every unrelated scalar, PP, placement and compatibility mirror."""
        result = []
        for mon in mons or (self.mon,):
            row = self.row(mon)
            for field in ("current_hp", "status", "sleep_turns"):
                row.pop(field)
            result.append((row, list(ActiveMoveslot.objects.filter(pokemon=mon).order_by("slot").values()),
                           list(PokemonPlacement.objects.filter(pokemon=mon).values()),
                           list(mon.active_slots.values()), list(mon.stored_users.values_list("pk", flat=True)),
                           list(mon.boxes.values_list("pk", flat=True))))
        return result

    def flow(self, key):
        """Buy, inspect, target, use and reload one of the fourteen definitions."""
        item = FIELD_RECOVERY_ITEMS[key]
        mons = [self.mon]
        if item.effect == "revive":
            self.state(current_hp=0)
        if item.target_scope == "party":
            reserve = self.create_mon(6)
            self.state(reserve, current_hp=0, status="brn", sleep_turns=None)
            mons.append(reserve)
        sheet = self.command("3", "party")
        identifier = re.search(r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", strip_ansi(sheet))
        self.assertIsNotNone(identifier)
        self.assertEqual(identifier.group(), str(self.mon.pk))
        self.room.db.store_inventory = {item.name: {"price": item.price, "quantity": 5}}
        item_store.node_buy(self.caller, item.name + " 2")
        purchase = self.caller.messages[-1]
        self.assertIn("You purchase 2 x " + item.name, purchase)
        self.assertEqual(Trainer.objects.get(pk=self.trainer.pk).money, 200000 - item.price * 2)
        self.assertEqual(self.room.db.store_inventory[item.name]["quantity"], 3)
        self.assertEqual(self.trainer.get_item_quantity(item.name), 2)
        inventory = self.command("", "inventory")
        self.assertIn(item.name + " x2 - " + item.desc, inventory)
        categories = format_inventory_by_category(gather_inventory_pairs(self.caller))
        self.assertIn("|wMedicine|n", categories)
        self.assertIn(item.name, categories)
        detail = self.command(item.name, "itemdex")
        self.assertIn("Category: Medicine", detail)
        self.assertIn(f"Reference price: ${item.price}", detail)
        before = self.preserved(*mons)
        hp_before = self.row()["current_hp"]
        selector = "party" if item.target_scope == "party" else identifier.group()
        args = item.name + "=" + selector
        output = self.command(args)
        self.assertEqual(output, "Used " + item.name + " on " + selector + ".")
        expected_hp = min(self.maximum, hp_before + item.amount) if item.effect == "heal" else self.maximum if item.effect == "revive" else hp_before
        self.assertEqual(self.row()["current_hp"], expected_hp)
        self.assertEqual((self.row()["status"], self.row()["sleep_turns"]),
                         ("", None) if item.effect == "status" else ("slp", 2))
        self.assertEqual(self.preserved(*mons), before)
        self.assertEqual(self.trainer.get_item_quantity(key), 1)
        for mon in mons:
            OwnedPokemon.flush_cached_instance(mon)
            fresh = OwnedPokemon.objects.get(pk=mon.pk)
            self.assertIsNot(fresh, mon)
            if item.effect == "revive":
                self.assertEqual(fresh.current_hp, get_max_hp(fresh))
            else:
                self.assertEqual(fresh.current_hp, expected_hp)
        result_sheet = self.command("3", "party")
        self.assertIn(str(self.mon.pk), result_sheet)
        if item.effect != "heal":
            completed = [self.row(mon) for mon in mons]
            self.assertIn("No item was consumed", self.command(args))
            self.assertEqual([self.row(mon) for mon in mons], completed)
            self.assertEqual(self.trainer.get_item_quantity(key), 1)
        WALKTHROUGH.append({"item": item.name, "effect": item.effect, "scope": item.target_scope,
                            "reference_price": item.price,
                            "commands": ["+party 3", "shop Buy: " + item.name + " 2", "+inventory",
                                         "+itemdex " + item.name, "+use " + args, "+party 3 after SQL reload"],
                            "purchase_output": purchase, "use_output": output,
                            "hp_before": hp_before, "hp_after": self.row()["current_hp"],
                            "status_after": self.row()["status"], "sleep_after": self.row()["sleep_turns"],
                            "bag_after": 1, "revived_count": len(mons) if item.effect == "revive" else 0,
                            "other_state_preserved": True})

    def test_hp_caps_fainted_guards_and_full_hp_retries_for_all_five(self):
        """Fixed HP effects never revive or consume on already-full targets."""
        for key, item in FIELD_RECOVERY_ITEMS.items():
            if item.effect != "heal":
                continue
            with self.subTest(item=item.name):
                self.give(key)
                self.state(current_hp=self.maximum - 1)
                self.command(item.name + "=3")
                self.assertEqual(self.row()["current_hp"], self.maximum)
                for hp in (self.maximum, 0):
                    self.state(current_hp=hp)
                    self.command(item.name + "=3")
                    self.assertEqual(self.row()["current_hp"], hp)
                    self.assertIn("No item was consumed", self.caller.messages[-1])
                self.assertEqual(self.trainer.get_item_quantity(key), 1)

    def test_existing_shop_editor_compact_stock_key_then_ordinary_full_name_use(self):
        """Keep staff catalog setup separate and use the existing editor grammar."""
        from types import SimpleNamespace

        setup_messages = []
        staff_fixture = SimpleNamespace(location=self.room, msg=setup_messages.append)
        item_store.node_edit(staff_fixture, "add FreshWater 200 5")
        self.assertIn("Added FreshWater.", setup_messages)
        item_store.node_buy(self.caller, "FreshWater 1")
        self.assertEqual(self.trainer.get_item_quantity("Fresh Water"), 1)
        self.assertEqual(Trainer.objects.get(pk=self.trainer.pk).money, 199800)
        self.assertIn("Fresh Water x1", self.command("", "inventory"))
        self.command("Fresh Water=3")
        self.assertEqual(self.row()["current_hp"], 31)
        self.assertEqual(self.trainer.get_item_quantity("FreshWater"), 0)

    def status_case(self, key, status):
        """Test each major status through the real command, not an effect mock."""
        self.give(key)
        self.state(current_hp=self.maximum, status=status, sleep_turns=2 if status == "slp" else None)
        before = self.preserved()
        self.command(FIELD_RECOVERY_ITEMS[key].name + "=3")
        self.assertEqual((self.row()["current_hp"], self.row()["status"], self.row()["sleep_turns"]),
                         (self.maximum, "", None))
        self.assertEqual(self.preserved(), before)
        self.assertEqual(self.trainer.get_item_quantity(key), 1)
        self.state(current_hp=0, status=status)
        before = self.row()
        self.command(FIELD_RECOVERY_ITEMS[key].name + "=3")
        self.assertEqual(self.row(), before)
        self.assertEqual(self.trainer.get_item_quantity(key), 1)

    def test_party_scope_excludes_eggs_boxes_living_and_all_fusion_reservations(self):
        """Sacred Ash cannot revive anything outside the canonical eligible party."""
        egg, boxed, fused = self.create_mon(1), self.create_mon(2), self.create_mon(4)
        self.state(egg, current_hp=0, is_egg=True)
        self.state(boxed, current_hp=0)
        self.state(fused, current_hp=0)
        PlacementService(self.storage).to_box(boxed)
        PlacementService(self.storage).reserve_for_fusion(fused)
        self.caller.db.fusion_id = str(fused.pk)
        self.give("Sacred Ash")
        before = [self.row(mon) for mon in (self.mon, egg, boxed, fused)]
        self.command("Sacred Ash=party")
        self.assertIn("No item was consumed", self.caller.messages[-1])
        self.assertEqual([self.row(mon) for mon in (self.mon, egg, boxed, fused)], before)
        self.assertEqual(self.trainer.get_item_quantity("Sacred Ash"), 2)
        self.state(current_hp=0)
        self.command("Sacred Ash=party")
        self.assertEqual(self.row()["current_hp"], self.maximum)
        self.assertEqual([self.row(mon) for mon in (egg, boxed, fused)], before[1:])
        self.assertEqual(self.trainer.get_item_quantity("Sacred Ash"), 1)

    def test_empty_party_and_invalid_scope_or_move_selector_do_not_consume(self):
        """Party revival requires explicit =party and accepts no single selector."""
        self.give("Sacred Ash")
        self.give("Fresh Water")
        self.state(current_hp=0)
        before = self.row()
        for args in ("Sacred Ash", "Sacred Ash=3", f"Sacred Ash={self.mon.pk}", "Sacred Ash=fusion",
                     "Sacred Ash=party/1", "Fresh Water=3/Water Gun", "Fresh=3"):
            self.command(args)
            self.assertEqual(self.row(), before)
        self.assertEqual(self.trainer.get_item_quantity("Sacred Ash"), 2)
        self.assertEqual(self.trainer.get_item_quantity("Fresh Water"), 2)
        PlacementService(self.storage).to_box(self.mon)
        self.command("Sacred Ash=party")
        self.assertIn("No item was consumed", self.caller.messages[-1])
        self.assertEqual(self.row(), before)

    def test_single_target_guards_owner_box_egg_and_inactive_fusion(self):
        """New single-target items keep all the common service prerequisites."""
        self.give("Fresh Water")
        other = ObjectDB.objects.create(db_key="other-" + uuid4().hex)
        trainer = Trainer.objects.create(user=other, trainer_number=Trainer.objects.count() + 1)
        foreign = create_owned_pokemon("Eevee", trainer, 20, ivs=[0] * 6, evs=[0] * 6, nature="Hardy")
        before = self.row()
        for target in ("1", str(foreign.pk), "Missing"):
            self.command("Fresh Water=" + target)
            self.assertEqual(self.row(), before)
        self.state(is_egg=True)
        before = self.row()
        self.command("Fresh Water=3")
        self.assertEqual(self.row(), before)
        self.state(is_egg=False)
        PlacementService(self.storage).to_box(self.mon)
        before = self.row()
        self.command("Fresh Water=" + str(self.mon.pk))
        self.assertEqual(self.row(), before)
        PlacementService(self.storage).reserve_for_fusion(self.mon)
        self.command("Fresh Water=fusion")
        self.assertEqual(self.row(), before)
        self.assertEqual(self.trainer.get_item_quantity("Fresh Water"), 2)

    def test_current_fusion_single_target_route_and_party_exclusion(self):
        """The current Fusion retains single-target food and Max Honey support."""
        PlacementService(self.storage).reserve_for_fusion(self.mon)
        self.caller.db.fusion_id = str(self.mon.pk)
        self.give("Fresh Water")
        self.command("Fresh Water=fusion")
        self.assertEqual(self.row()["current_hp"], 31)
        self.state(current_hp=0)
        self.give("Max Honey")
        self.command("Max Honey=self")
        self.assertEqual(self.row()["current_hp"], self.maximum)

    def test_ambiguous_names_normalized_full_items_and_legacy_inventory_aliases(self):
        """Full normalized names work, while duplicate Pokemon names stay safe."""
        second = self.create_mon(6)
        InventoryEntry.objects.create(owner=self.trainer, item_name="Fresh Water", quantity=1)
        InventoryEntry.objects.create(owner=self.trainer, item_name="fresh-water", quantity=1)
        before = self.row()
        self.command("Fresh Water=Food Test")
        self.assertEqual(self.row(), before)
        self.assertEqual(self.trainer.get_item_quantity("Fresh Water"), 2)
        self.command("FRESH-WATER=3")
        self.assertEqual(self.row()["current_hp"], 31)
        self.assertEqual(self.trainer.get_item_quantity("Fresh Water"), 1)
        self.assertEqual(self.row(second)["current_hp"], 1)

    def test_battle_guard_at_command_and_locked_service(self):
        """An item queued before a battle must still fail at the locked boundary."""
        self.state(current_hp=0)
        self.give("Sacred Ash")
        self.give("Max Honey")
        self.caller.db.battle_lock = "fixture-battle"
        before = self.row()
        self.command("Sacred Ash=party")
        self.assertIsNone(FieldFoodUse(self.caller).use("Max Honey", "3"))
        self.assertEqual(self.row(), before)
        self.assertEqual(self.trainer.get_item_quantity("Sacred Ash"), 2)
        self.assertEqual(self.trainer.get_item_quantity("Max Honey"), 2)

    def test_missing_inventory_living_revive_and_failed_debit_do_not_mutate(self):
        """Missing/ineffective uses and a rejected debit never grant a free heal."""
        before = self.row()
        self.command("Fresh Water=3")
        self.assertEqual(self.row(), before)
        self.give("Max Honey")
        self.command("Max Honey=3")
        self.assertEqual(self.row(), before)
        self.state(current_hp=0)
        self.give("Sacred Ash")
        before = self.row()
        with patch.object(Trainer, "remove_item", return_value=False) as debit:
            self.command("Sacred Ash=party")
        self.assertEqual(debit.call_count, 1)
        self.assertEqual(self.row(), before)
        self.assertEqual(self.trainer.get_item_quantity("Sacred Ash"), 2)

    def test_later_party_save_failure_rolls_back_all_members_debit_and_cache(self):
        """A failed second durable write cannot leave a partly revived party."""
        second = self.create_mon(6)
        for mon in (self.mon, second):
            self.state(mon, current_hp=0)
        self.give("Sacred Ash")
        before = [self.row(mon) for mon in (self.mon, second)]
        original, saves = OwnedPokemon.save, []

        def fail_second(pokemon, *args, **kwargs):
            """Inject failure after SQL, never substitute successful effects."""
            original(pokemon, *args, **kwargs)
            saves.append(pokemon.pk)
            if len(saves) == 2:
                raise RuntimeError("injected second party write")

        with patch.object(OwnedPokemon, "save", fail_second):
            with self.assertRaisesRegex(RuntimeError, "second party write"):
                self.command("Sacred Ash=party")
        self.assertEqual([self.row(mon) for mon in (self.mon, second)], before)
        self.assertEqual((self.mon.current_hp, second.current_hp), (0, 0))
        self.assertEqual(self.trainer.get_item_quantity("Sacred Ash"), 2)
        self.command("Sacred Ash=party")
        self.assertEqual([self.row(mon)["current_hp"] for mon in (self.mon, second)], [self.maximum] * 2)
        self.assertEqual(self.trainer.get_item_quantity("Sacred Ash"), 1)

    def test_conflicting_party_owner_blocks_every_member_before_debit(self):
        """A corrupt canonical membership cannot silently heal another owner."""
        second = self.create_mon(6)
        other = ObjectDB.objects.create(db_key="conflict-" + uuid4().hex)
        trainer = Trainer.objects.create(user=other, trainer_number=Trainer.objects.count() + 1)
        for mon in (self.mon, second):
            self.state(mon, current_hp=0)
        self.state(second, trainer=trainer)
        self.give("Sacred Ash")
        before = [self.row(mon) for mon in (self.mon, second)]
        self.command("Sacred Ash=party")
        self.assertEqual([self.row(mon) for mon in (self.mon, second)], before)
        self.assertEqual(self.trainer.get_item_quantity("Sacred Ash"), 2)

    def race(self, *actions):
        """Compete on independent PostgreSQL connections at a common barrier."""
        barrier = Barrier(len(actions))

        def run(action):
            """Close every thread connection even after a failed transaction."""
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return action()
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            return list(pool.map(run, actions))

    def test_concurrent_party_completions_consume_only_one_item(self):
        """A waiting replay sees the already revived party, including every row."""
        second = self.create_mon(6)
        for mon in (self.mon, second):
            self.state(mon, current_hp=0)
        self.give("Sacred Ash")
        use = lambda: FieldFoodUse(self.caller).use("Sacred Ash", "party")
        self.assertCountEqual(self.race(use, use), [True, False])
        self.assertEqual(self.trainer.get_item_quantity("Sacred Ash"), 1)
        self.assertEqual([self.row(mon)["current_hp"] for mon in (self.mon, second)], [self.maximum] * 2)

    def test_concurrent_party_and_single_revival_cannot_spend_both(self):
        """One fainted target can benefit from just one competing full revival."""
        self.state(current_hp=0)
        self.give("Sacred Ash", 1)
        self.give("Max Honey", 1)
        self.assertCountEqual(self.race(lambda: FieldFoodUse(self.caller).use("Sacred Ash", "party"),
                                        lambda: FieldFoodUse(self.caller).use("Max Honey", "3")), [True, False])
        self.assertEqual(self.row()["current_hp"], self.maximum)
        self.assertEqual(self.trainer.get_item_quantity("Sacred Ash") + self.trainer.get_item_quantity("Max Honey"), 1)

    def test_concurrent_deposit_preserves_the_legal_party_revival_order(self):
        """A box move and party healing serialize using the same storage lock."""
        self.state(current_hp=0)
        self.give("Sacred Ash")
        results = self.race(lambda: FieldFoodUse(self.caller).use("Sacred Ash", "party"),
                            lambda: PlacementService(self.storage).to_box(self.mon))
        self.assertEqual(PokemonPlacement.objects.get(pokemon=self.mon).location_type, "box")
        self.assertEqual(self.row()["current_hp"], self.maximum if results[0] else 0)
        self.assertEqual(self.trainer.get_item_quantity("Sacred Ash"), 1 if results[0] else 2)


def flow_test(key):
    """Report each item's real shop, display, use and SQL-reload flow separately."""
    def test(self):
        """Acquire and use a selected non-plot field medicine equivalent."""
        self.flow(key)
    return test


def status_test(key, status):
    """Report each of the seven cures against all six major status codes."""
    def test(self):
        """Cure one saved condition and reject its fainted counterpart."""
        self.status_case(key, status)
    return test


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from evennia.commands.command import Command
        with patch.object(evennia, "Command", Command):
            from commands.player.cmd_inventory import CmdInventory, CmdUseItem
            from commands.player.cmd_pokedex import CmdItemdexSearch
            from commands.player.cmd_sheet import CmdSheetPokemon
        from django.db import close_old_connections, connections
        from evennia.objects.models import ObjectDB
        from evennia.utils.ansi import strip_ansi
        from menus import item_store
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon, get_max_hp
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.models.storage import PokemonPlacement, UserStorage
        from pokemon.models.trainer import InventoryEntry, Trainer
        from pokemon.services.field_food import FieldFoodUse
        from pokemon.services.placement import PlacementService
        from pokemon.user import User
        from utils.inventory_view import format_inventory_by_category, gather_inventory_pairs

        for key, item in FIELD_RECOVERY_ITEMS.items():
            setattr(FoodCases, "test_flow_" + key, flow_test(key))
            if item.effect == "status":
                for status in ("brn", "psn", "tox", "frz", "slp", "par"):
                    setattr(FoodCases, "test_cure_" + key + "_" + status, status_test(key, status))
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FoodCases))
        print("FIELD_FOOD_PLAYER_WALKTHROUGH " + json.dumps(WALKTHROUGH))
        raise SystemExit(not result.wasSuccessful())

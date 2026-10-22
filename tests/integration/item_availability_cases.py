"""Acquire-to-use ordinary commands in an explicitly disposable PostgreSQL world.

Room stock, wallets and native targets are fixture setup. No bag items are
granted: acquisitions use the real store menu or authored dispenser. Captured
transport is automated command acceptance, never a live login or live stock.
"""

import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
from ui_cases import PlayerView as SessionTransport

EVIDENCE = []
FIELD = {
    "Potion": ("3", {"current_hp": 1}, "current_hp"),
    "Revive": ("3", {"current_hp": 0}, "current_hp"),
    "Ether": ("3/Water Gun", {}, "pp"),
    "Energy Root": ("3", {"current_hp": 1}, "current_hp"),
    "Revival Herb": ("3", {"current_hp": 0}, "current_hp"),
    "Oran Berry": ("3", {"current_hp": 1}, "current_hp"),
    "Pecha Berry": ("3", {"status": "psn"}, "status"),
    "Leppa Berry": ("3/Water Gun", {}, "pp"),
    "Mystery Berry": ("3/Water Gun", {}, "pp"),
    "Pomeg Berry": ("3", {"evs": [20, 0, 0, 0, 0, 0]}, "evs"),
    "Fresh Water": ("3", {"current_hp": 1}, "current_hp"),
    "Max Honey": ("3", {"current_hp": 0}, "current_hp"),
    "Sacred Ash": ("party", {"current_hp": 0}, "current_hp"),
    "Protein": ("3", {}, "evs"),
    "Health Feather": ("3", {}, "evs"),
    "Ability Capsule": ("3", {}, "ability"),
    "Ability Patch": ("3", {}, "ability"),
    "Bottle Cap": ("3/Atk", {}, "flags"),
    "Gold Bottle Cap": ("3", {}, "flags"),
}
EVOLUTIONS = {
    "Fire Stone": ("Vulpix", "Ninetales"),
    "Peat Block": ("Ursaring", "Ursaluna"),
    "Scroll of Darkness": ("Kubfu", "Urshifu"),
    "Scroll of Waters": ("Kubfu", "Urshifu-Rapid-Strike"),
}


class AcquisitionPlayer(SessionTransport):
    """Adapt transport and delegate real inventory, currency and target methods."""

    def __getattr__(self, name):
        """Bind ordinary production User methods without introducing staff APIs."""
        if name in {"add_item", "remove_item", "has_item", "spend_money", "add_money",
                    "get_active_pokemon_by_slot", "get_pokemon_by_id"}:
            return getattr(User, name).__get__(self, type(self))
        raise AttributeError(name)

    def check_permstring(self, permission):
        """The ordinary menu must never expose the Builder stock editor."""
        return False

    def search(self, query, **kwargs):
        """Resolve only this fixture's named objects, as captured transport."""
        return next((obj for obj in self.location.contents if obj.key == query), None)


class AcquisitionCases(unittest.TestCase):
    """Verify real stock debit, wallet, bag, effect, negatives and SQL reload."""

    def setUp(self):
        """Create tagged ordinary identities and explicitly separate stock setup."""
        room = ObjectDB.objects.create(db_key="availability-772-room-" + uuid4().hex)
        self.room = SimpleNamespace(id=room.pk, pk=room.pk, key=room.key, db=room.db,
                                    ndb=room.ndb, attributes=room.attributes, contents=[])
        self.room.db.is_item_shop = True
        self.room.db.store_inventory = {}
        self.players, self.mons, self.session = [], [], None
        for _ in range(2):
            character = ObjectDB.objects.create(db_key="availability-772-player-" + uuid4().hex,
                                                db_typeclass_path="pokemon.user.User")
            player = AcquisitionPlayer(character, character.trainer, character.storage)
            player.pk, player.location = character.pk, self.room
            self.players.append(player)
            self.room.contents.append(player)
        self.player = self.players[0]
        self.player.trainer.money = 200000
        self.player.trainer.save(update_fields=["money"])
        self.search_patch = patch("pokemon.battle.battleinstance.search_object",
                                  lambda query: [p for p in self.players if str(p.id) == str(query).lstrip("#")])
        self.search_patch.start()
        self.addCleanup(self.search_patch.stop)
        self.mon = self.native("Mew", 3)

    def tearDown(self):
        """Close only local fixture menus and battles before schema removal."""
        for player in self.players:
            if player.ndb._evmenu:
                player.ndb._evmenu.close_menu()
        if self.session:
            self.session.end()

    def native(self, species, slot, player=None):
        """Prepare owned native species with real calculated stats, no held item."""
        player = player or self.player
        from pokemon.names import resolve_dex_entry
        from pokemon.dex import POKEDEX
        data = resolve_dex_entry(POKEDEX, species)
        mon = create_owned_pokemon(species, player.trainer, 50, nature="Hardy", ability=data.raw["abilities"]["0"],
                                   gender=data.raw.get("gender", "M"),
                                   ivs=[0] * 6, evs=[0] * 6,
                                   active_move_names=["Tackle", "Water Gun"] if species == "Mew" else None)
        PlacementService(player.storage).to_party(mon, slot=slot)
        self.mons.append(mon)
        return mon

    def state(self):
        """Read SQL and reset attribute caches instead of trusting model identity."""
        self.room.attributes.reset_cache()
        return {"wallet": Trainer.objects.filter(pk=self.player.trainer.pk).values_list("money", flat=True).get(),
                "stock": dict(self.room.db.store_inventory or {}),
                "bag": list(self.player.trainer.inventory.order_by("item_name").values("item_name", "quantity")),
                "owned": [dict(row, pk=row[OwnedPokemon._meta.pk.name]) for row in
                          OwnedPokemon.objects.filter(pk__in=[m.pk for m in self.mons]).order_by("pk").values()],
                "pp": list(ActiveMoveslot.objects.filter(pokemon=self.mon).order_by("slot").values("slot", "move__name", "current_pp"))}

    def command(self, name, args="", side=0):
        """Use production command parsing; capture only client transport."""
        module, cls = COMMANDS[name]
        command = cls()
        command.caller, command.args, command.cmdstring = self.players[side], args, "+" + name
        command.parse()
        if hasattr(module, "get_system"):
            with patch.object(module, "get_system", return_value=SimpleNamespace(battle_manager=None)):
                command.func()
        else:
            command.func()
        return command.caller.messages[-1]

    def reply(self, text):
        """Route store choices through Evennia's real bound menu command."""
        command = CmdEvMenuNode()
        command.caller, command.raw_string, command.session = self.player, text, None
        command.func()

    def buy(self, item, *, price=100, quantity=2):
        """Author disposable stock, then purchase with actual +store/menu inputs."""
        self.room.db.store_inventory = {item: {"price": price, "quantity": quantity}}
        before = self.state()
        self.assertEqual(self.player.trainer.get_item_quantity(item), 0)
        start = len(self.player.messages)
        self.command("store")
        self.assertNotIn("Edit inventory", "\n".join(map(str, self.player.messages[start:])))
        self.reply("1")
        self.reply(item + " 1")
        self.reply("back")
        self.reply("q")
        self.assertIsNone(self.player.ndb._evmenu)
        self.assertEqual(self.player.trainer.get_item_quantity(item), 1)
        after = self.state()
        self.assertEqual(after["wallet"], before["wallet"] - price)
        self.assertEqual(after["stock"][item]["quantity"], quantity - 1)
        self.assertIn("purchase 1 x " + item, "\n".join(map(str, self.player.messages[start:])))
        self.command("inventory")
        EVIDENCE.append({"label": "configured-shop-acquisition", "item": item,
                         "commands": ["+store", "1", item + " 1", "back", "q", "+inventory"],
                         "setup": "Disposable shop stock, wallet and native targets; initially empty item bag",
                         "before": before, "after": after, "messages": self.player.messages[start:]})

    def record_effect(self, item, command, before):
        """Retain actual effect and SQL reload independently of source availability."""
        old = self.mon
        OwnedPokemon.flush_cached_instance(old)
        self.mon = OwnedPokemon.objects.get(pk=old.pk)
        self.assertIsNot(self.mon, old)
        EVIDENCE.append({"label": "acquired-item-effect-reload", "item": item,
                         "commands": [command, "SQL reload"], "before": before, "after": self.state(),
                         "messages": self.player.messages[-4:]})

    def field(self, item):
        """Buy a useful item, apply its ordinary field route, then reload SQL."""
        target, updates, changed = FIELD[item]
        if item in {"Ability Capsule", "Ability Patch"}:
            PlacementService(self.player.storage).to_box(self.mon)
            self.mon = self.native("Eevee", 3)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(**updates)
        ActiveMoveslot.objects.filter(pokemon=self.mon).update(current_pp=1)
        self.buy(item)
        before = self.state()
        self.command("use", item + "=" + target)
        after = self.state()
        self.assertEqual(self.player.trainer.get_item_quantity(item), 0, self.player.messages)
        if changed == "pp":
            self.assertNotEqual(before["pp"], after["pp"])
        else:
            old = next(row for row in before["owned"] if row["pk"] == self.mon.pk)
            new = next(row for row in after["owned"] if row["pk"] == self.mon.pk)
            self.assertNotEqual(old[changed], new[changed])
        self.assertEqual(after["wallet"], before["wallet"])
        self.assertEqual(after["stock"], before["stock"])
        self.record_effect(item, "+use " + item + "=" + target, before)

    def evolve(self, item):
        """Buy a bag evolution item and use the complete-ID player command."""
        source, target = EVOLUTIONS[item]
        PlacementService(self.player.storage).to_box(self.mon)
        self.mon = self.native(source, 3)
        self.buy(item)
        before = self.state()
        args = str(self.mon.pk) + " " + item
        self.command("evolve", args)
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("species", flat=True).get(), target)
        self.assertEqual(self.player.trainer.get_item_quantity(item), 0)
        self.record_effect(item, "+evolve " + args, before)

    def test_authored_alpha_candy_vend_to_use(self):
        """Reproduce the repository's alpha recipe, without claiming it is live."""
        vendor = ObjectDB.objects.create(db_key="Alpha Candy Dispenser", db_typeclass_path="typeclasses.vendors.PokeballVendor")
        vendor.db.dispense_item, vendor.db.dispense_quantity, vendor.db.stock = "rarecandy", 5, None
        self.room.contents.append(vendor)
        before = self.state()
        self.command("vend", "Alpha Candy Dispenser 1")
        self.assertEqual(self.player.trainer.get_item_quantity("Rare Candy"), 5)
        self.command("use", "Rare Candy=3")
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("level", flat=True).get(), 51)
        self.assertEqual(self.player.trainer.get_item_quantity("Rare Candy"), 4)
        self.assertEqual(self.state()["wallet"], before["wallet"])
        self.record_effect("Rare Candy", "+vend Alpha Candy Dispenser 1; +use Rare Candy=3", before)

    def test_pp_capacity_purchase_prompt_selection_and_reload(self):
        """Both capacity items must come from stock and select the real move."""
        for item in ("PP Up", "PP Max"):
            self.buy(item)
            before = self.state()
            self.command("use", item + "=3")
            self.command("use", "1")
            self.assertEqual(self.player.trainer.get_item_quantity(item), 0)
            self.assertNotEqual(self.state()["pp"], before["pp"])
            self.record_effect(item, "+use " + item + "=3; +use 1", before)

    def test_shop_to_sweet_and_trade_held_evolution(self):
        """Buying and equipping the real copy enables both non-plot equivalents."""
        for item, species, target in (("Strawberry Sweet", "Milcery", "Alcremie"),
                                      ("Metal Coat", "Onix", "Steelix")):
            PlacementService(self.player.storage).to_box(self.mon)
            self.mon = self.native(species, 3)
            self.buy(item)
            before = self.state()
            self.command("hold", "3=" + item)
            self.command("evolve", str(self.mon.pk))
            self.assertEqual(OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("species", flat=True).get(), target,
                             self.player.messages[-3:])
            self.assertEqual(self.player.trainer.get_item_quantity(item), 0)
            self.assertEqual(OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("held_item", flat=True).get(), "")
            self.record_effect(item, "+hold 3=" + item + "; +evolve " + str(self.mon.pk), before)

    def test_shop_to_leftovers_battle_healing_and_reload(self):
        """A purchased reusable held item has a real residual effect in battle."""
        self.buy("Leftovers")
        self.command("hold", "3=Leftovers")
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=1)
        OwnedPokemon.flush_cached_instance(self.mon)
        self.mon = OwnedPokemon.objects.get(pk=self.mon.pk)
        before = self.state()
        foe = create_battle_pokemon("Magikarp", 100, is_wild=True, move_names=["Splash"])
        self.session = BattleSession(self.player)
        self.session._track_temp_opponent_team([foe])
        self.session._select_opponent = lambda: (foe, "Wild Magikarp", BattleType.WILD, "Controlled fixture")
        self.session.start()
        self.command("attack", "Water Gun")
        holder = self.session.battle.participants[0].active[0]
        self.assertEqual(holder.hp, 1 + holder.max_hp // 16)
        self.assertEqual(self.player.trainer.get_item_quantity("Leftovers"), 0)
        self.session.end()
        self.session = None
        self.command("hold", "3=")
        self.assertEqual(self.player.trainer.get_item_quantity("Leftovers"), 1)
        self.record_effect("Leftovers", "+hold 3=Leftovers; +attack Water Gun; wild Magikarp uses Splash; +hold 3=", before)

    def test_unaffordable_and_insufficient_stock_do_not_grant_items(self):
        """Expected purchase restrictions preserve the entire bag and wallet."""
        self.room.db.store_inventory = {"Potion": {"price": 300000, "quantity": 1}}
        before = self.state()
        self.command("store")
        self.reply("1")
        self.reply("Potion 1")
        self.reply("Potion 2")
        self.reply("back")
        self.reply("q")
        self.assertEqual(self.state(), before)
        EVIDENCE.append({"label": "expected-restriction", "commands": ["+store", "1", "Potion 1", "Potion 2"],
                         "finding": "Insufficient money/stock creates no item and spends no money",
                         "before": before, "after": self.state()})

    def test_empty_and_absent_shop_do_not_grant_items(self):
        """Definition presence and shop flags cannot create stock or debit money."""
        before = self.state()
        self.command("store")
        self.reply("1")
        self.reply("Potion 1")
        self.reply("back")
        self.reply("q")
        self.assertEqual(self.state(), before)
        self.room.db.is_item_shop = False
        self.assertEqual(self.command("store"), "There is no store here.")
        self.assertEqual(self.state(), before)
        EVIDENCE.append({"label": "expected-restriction", "commands": ["+store", "Potion 1"],
                         "finding": "An empty or absent shop grants nothing", "before": before, "after": self.state()})

    def test_unconfigured_itemfinder_rate_grants_no_item(self):
        """A rate without an explicitly reviewed source gives no phantom promise."""
        self.room.db.allow_hunting, self.room.db.itemfinder_rate = True, 100
        self.room.db.noitem = False
        self.room.db.npc_chance, self.room.db.encounter_rate = 0, 0
        before = self.state()
        self.assertEqual(self.command("hunt"), "You didn't find any Pokémon.")
        self.assertEqual(self.state(), before)
        EVIDENCE.append({"label": "expected-restriction", "commands": ["+hunt"],
                         "finding": "No named finder source grants nothing and makes no item promise",
                         "before": before, "after": self.state()})

    def test_hunt_chart_held_item_is_not_an_acquisition_source(self):
        """Authored held metadata is currently ignored by the normal wild route."""
        self.room.db.allow_hunting = True
        self.room.db.itemfinder_rate, self.room.db.npc_chance = 0, 0
        self.room.db.encounter_rate = 100
        self.room.db.hunt_chart = [{"name": "Rattata", "min_level": 5, "max_level": 5,
                                   "weight": 1, "held_item": "Oran Berry"}]
        before = self.state()
        self.command("hunt")
        self.session = self.player.ndb.battle_instance
        self.assertIsNotNone(self.session)
        foe = self.session.battle.participants[1].active[0]
        self.assertFalse(foe.item)
        identifier = foe.model_id.removeprefix("encounter:")
        self.assertEqual(EncounterPokemon.objects.filter(pk=identifier).values_list("held_item", flat=True).get(), "")
        self.assertEqual(self.state()["bag"], before["bag"])
        EVIDENCE.append({"label": "missing-acquisition-pipeline", "commands": ["+hunt"],
                         "finding": "A hunt-chart held_item does not reach the runtime or encounter row",
                         "held_runtime": str(foe.item or ""), "held_sql": "", "bag_unchanged": True})

    def test_shop_to_held_escape_and_return_to_bag(self):
        """Buy Smoke Ball, equip normally, flee a real wild session, then remove."""
        self.buy("Smoke Ball")
        before = self.state()
        self.command("hold", "3=Smoke Ball")
        self.assertEqual(self.player.trainer.get_item_quantity("Smoke Ball"), 0)
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("held_item", flat=True).get(), "Smoke Ball")
        foe = create_battle_pokemon("Dugtrio", 50, is_wild=True, move_names=["Sand Attack"])
        self.session = BattleSession(self.player)
        self.session._track_temp_opponent_team([foe])
        self.session._select_opponent = lambda: (foe, "Wild Dugtrio", BattleType.WILD, "Controlled fixture")
        self.session.start()
        battle = self.session.battle
        self.session._sync_active_battle_state()
        self.session._persist_turn_state()
        battle_handler.unregister(self.session)
        self.player.ndb.battle_instance = None
        self.room.ndb.battle_instances = {}
        self.session = BattleSession.restore(self.room, self.session.battle_id)
        self.assertIsNotNone(self.session)
        battle = self.session.battle
        self.command("flee")
        self.assertEqual(battle._flee_result["reason"], "smokeball")
        self.assertTrue(battle._flee_result["success"])
        self.command("hold", "3=")
        self.assertEqual(self.player.trainer.get_item_quantity("Smoke Ball"), 1)
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("held_item", flat=True).get(), "")
        self.record_effect("Smoke Ball", "+hold 3=Smoke Ball; checkpoint restore; +flee; +hold 3=", before)


def add_case(item, method):
    """Count each reviewed acquire-to-effect item separately."""
    def test(self):
        """Exercise the named item with real stock, wallet, inventory and effect."""
        getattr(self, method)(item)
    setattr(AcquisitionCases, "test_" + method + "_" + "".join(c for c in item.lower() if c.isalnum()), test)


for name in FIELD:
    add_case(name, "field")
for name in EVOLUTIONS:
    add_case(name, "evolve")


def load_runtime():
    """Load production models only after the explicit schema guard is active."""
    global ObjectDB, CmdEvMenuNode, BattleSession, BattleType, create_battle_pokemon
    global battle_handler, create_owned_pokemon, OwnedPokemon, EncounterPokemon
    global ActiveMoveslot, Trainer, PlacementService, User, COMMANDS
    import evennia
    from evennia.commands.command import Command
    from evennia.commands.cmdset import CmdSet
    with patch.object(evennia, "Command", Command), patch.object(evennia, "CmdSet", CmdSet):
        from commands.player import (cmd_store, cmd_vendor, cmd_inventory, cmd_party,
                                     cmd_learn_evolve, cmd_hunt, cmd_battle_flee, cmd_battle_attack)
    from evennia.objects.models import ObjectDB
    from evennia.utils.evmenu import CmdEvMenuNode
    from pokemon.battle.battleinstance import BattleSession, BattleType, create_battle_pokemon
    from pokemon.battle.handler import battle_handler
    from pokemon.helpers.pokemon_helpers import create_owned_pokemon
    from pokemon.models.core import OwnedPokemon, EncounterPokemon
    from pokemon.models.moves import ActiveMoveslot
    from pokemon.models.trainer import Trainer
    from pokemon.services.placement import PlacementService
    from pokemon.user import User
    COMMANDS = {"store": (cmd_store, cmd_store.CmdStore), "vend": (cmd_vendor, cmd_vendor.CmdVend),
                "inventory": (cmd_inventory, cmd_inventory.CmdInventory), "use": (cmd_inventory, cmd_inventory.CmdUseItem),
                "hold": (cmd_party, cmd_party.CmdSetHoldItem), "evolve": (cmd_learn_evolve, cmd_learn_evolve.CmdEvolvePokemon),
                "hunt": (cmd_hunt, cmd_hunt.CmdHunt), "flee": (cmd_battle_flee, cmd_battle_flee.CmdBattleFlee),
                "attack": (cmd_battle_attack, cmd_battle_attack.CmdBattleAttack)}


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        load_runtime()
        try:
            result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AcquisitionCases))
        finally:
            if os.environ.get("PF2_AVAILABILITY_EVIDENCE"):
                Path(os.environ["PF2_AVAILABILITY_EVIDENCE"]).write_text(json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())

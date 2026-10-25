"""Travel-to-effect for seven finite source recipes on disposable PostgreSQL.

The source/wallet/native conditions are explicitly separate setup. Ordinary
players acquire every item through +store; no inventory grants substitute for
the purchase flow. Captured transport is not a live login/public installation.
"""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import random
from threading import Barrier
import unittest
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
import item_availability_cases as acquisition
import item_supply_cases as six_supply

EVIDENCE = []
STATUS = {
    "Antidote": "tox",
    "Paralyze Heal": "par",
    "Awakening": "slp",
    "Burn Heal": "brn",
    "Ice Heal": "frz",
    "Full Heal": "psn",
}
STONES = {
    "Water Stone": ("Eevee", "Vaporeon"),
    "Thunder Stone": ("Eevee", "Jolteon"),
    "Leaf Stone": ("Eevee", "Leafeon"),
    "Ice Stone": ("Eevee", "Glaceon"),
    "Sun Stone": ("Gloom", "Bellossom"),
    "Moon Stone": ("Clefairy", "Clefable"),
}
VITAMINS = ("HP Up", "Protein", "Iron", "Calcium", "Zinc", "Carbos")


class FiniteSupplyCases(unittest.TestCase):
    """One current source revision, actual menus, SQL reload and useful effects."""

    native = acquisition.AcquisitionCases.native
    command = acquisition.AcquisitionCases.command
    reply = acquisition.AcquisitionCases.reply
    move = six_supply.ItemSupplyCases.move
    traverse = six_supply.ItemSupplyCases.traverse

    def state(self):
        """Include durable capacity rows as well as stock, money, bag and targets."""
        state = acquisition.AcquisitionCases.state(self)
        state["boosts"] = list(
            MovePPBoost.objects.filter(pokemon_id__in=[mon.pk for mon in self.mons])
            .order_by("pokemon_id", "move_id")
            .values("pokemon_id", "move_id", "bonus_pp")
        )
        return state

    def setUp(self):
        """Author only a fresh tagged hub and this test's selected finite counter."""
        acquisition.AcquisitionCases.setUp(self)
        self.route = FINITE_SUPPLY_ROUTES[self.issue]
        self.hub = create_object(
            "typeclasses.rooms.FusionRoom", key="finite-supply-hub-" + uuid4().hex, nohome=True
        )
        self.shop = self.route.install(self.hub)
        self.room = self.shop
        for player in self.players:
            player.location = self.hub
            ObjectDB.objects.filter(pk=player.pk).update(db_location_id=self.hub.pk)
            player.move_to = lambda destination, *args, _player=player, **kwargs: self.move(
                _player, destination
            )
        self.start = self.state()
        self.addCleanup(self.record)

    def tearDown(self):
        """Close current fixture sessions; remove only this tagged installed route."""
        if not hasattr(self, "final"):
            self.final = self.state()
        acquisition.AcquisitionCases.tearDown(self)
        receipt = BattleRewards.stored_attribute(self.hub, self.route.marker)
        if receipt:
            ObjectDB.objects.filter(
                pk__in=[receipt["room"], receipt["entrance"], receipt["return_exit"]]
            ).delete()
            self.hub.attributes.remove(self.route.marker)

    def record(self):
        """Keep actual command output and remaining stock without source availability claims."""
        # unittest runs cleanup after tearDown, so capture the stored terminal snapshot.
        EVIDENCE.append(
            {
                "case": self.id().split(".")[-1],
                "issue": self.issue,
                "setup": "Tagged hub, finite recipe, wallet and native target; initially empty bag",
                "initial": self.start,
                "final": getattr(self, "final", None),
                "messages": self.player.messages,
                "source": self.route.recipe(),
                "evidence_kind": "production command/menu with SQL",
            }
        )

    def finish(self):
        """Read the complete terminal SQL state before test-owned teardown."""
        self.final = self.state()

    def buy(self, item):
        """Traverse the actual public exit and purchase only existing authored stock."""
        if self.player.location.pk == self.hub.pk:
            self.traverse(self.route.entrance)
        before, count = self.state(), self.player.trainer.get_item_quantity(item)
        self.command("store")
        self.reply("1")
        self.reply(item + " 1")
        self.reply("back")
        self.reply("q")
        after = self.state()
        self.assertEqual(self.player.trainer.get_item_quantity(item), count + 1)
        self.assertEqual(after["wallet"], before["wallet"] - before["stock"][item]["price"])
        self.assertEqual(after["stock"][item]["quantity"], before["stock"][item]["quantity"] - 1)
        self.assertIn("purchase 1 x " + item, "\n".join(map(str, self.player.messages)))
        self.command("inventory")

    def field(self, item):
        """Use a purchased copy through the item's existing normal field route."""
        if item in STONES or item in {"Ability Capsule", "Ability Patch"}:
            PlacementService(self.player.storage).to_box(self.mon)
            self.mon = self.native(STONES[item][0] if item in STONES else "Eevee", 3)
        updates = {}
        if item in STATUS:
            updates = {"status": STATUS[item], "sleep_turns": 2 if item == "Awakening" else 0}
        elif item in {"Super Potion", "Hyper Potion"}:
            updates = {"current_hp": 1}
        elif item in {"Revive", "Max Revive"}:
            updates = {"current_hp": 0}
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(**updates)
        if self.issue == 879:
            for slot in ActiveMoveslot.objects.filter(pokemon=self.mon):
                MovePPBoost.objects.create(
                    pokemon=self.mon,
                    move=slot.move,
                    bonus_pp=PPCapacity.for_move(slot.move.name).stages[-1],
                )
            ActiveMoveslot.objects.filter(pokemon=self.mon).update(current_pp=0)
        self.buy(item)
        before = self.state()
        if item in STONES:
            self.command("evolve", str(self.mon.pk) + " " + item)
        else:
            target = "3/Water Gun" if item in {"Ether", "Max Ether"} else "3"
            self.command("use", item + "=" + target)
            if item in {"PP Up", "PP Max"}:
                self.command("use", "1")
        after = self.state()
        self.assertEqual(self.player.trainer.get_item_quantity(item), 0, self.player.messages[-6:])
        self.assertEqual(after["wallet"], before["wallet"])
        self.assertEqual(after["stock"], before["stock"])
        row = OwnedPokemon.objects.filter(pk=self.mon.pk).values().get()
        if item in STATUS:
            self.assertEqual(row["status"], "")
            self.assertIsNone(row["sleep_turns"])
        elif item in {"Super Potion", "Hyper Potion", "Revive", "Max Revive"}:
            cap = get_max_hp(OwnedPokemon.objects.get(pk=self.mon.pk))
            expected = {
                "Super Potion": min(cap, 61),
                "Hyper Potion": min(cap, 121),
                "Revive": cap // 2,
                "Max Revive": cap,
            }[item]
            self.assertEqual(row["current_hp"], expected)
        elif self.issue == 879:
            slots = list(ActiveMoveslot.objects.filter(pokemon=self.mon).order_by("slot"))
            for slot in slots:
                if "Ether" in item and normalize_name(slot.move.name) != "watergun":
                    expected = 0
                else:
                    maximum = PPCapacity.for_move(slot.move.name).base * 8 // 5
                    expected = maximum if item.startswith("Max") else 10
                self.assertEqual(slot.current_pp, expected)
        elif item in STONES:
            self.assertEqual(row["species"], STONES[item][1], self.player.messages[-3:])
        elif item in VITAMINS:
            expected = [0] * 6
            expected[VITAMINS.index(item)] = 10
            self.assertEqual(row["evs"], expected)
            if item == "HP Up":
                self.assertEqual(
                    row["current_hp"], get_max_hp(OwnedPokemon.objects.get(pk=self.mon.pk))
                )
        elif item in {"PP Up", "PP Max"}:
            selected = ActiveMoveslot.objects.get(pokemon=self.mon, slot=1)
            boost = MovePPBoost.objects.get(pokemon=self.mon, move=selected.move)
            stages = PPCapacity.for_move(selected.move.name).stages
            self.assertEqual(boost.bonus_pp, stages[-1] if item == "PP Max" else stages[1])
        else:
            previous = next(mon["ability"] for mon in before["owned"] if mon["pk"] == self.mon.pk)
            self.assertNotEqual(row["ability"], previous)
        self.assertIsNone(BattleRewards.stored_attribute(self.shop, "item_replenishment"))
        self.traverse("back")
        self.finish()

    def retry(self):
        """Installation and normal return travel preserve remaining stock and links."""
        item = self.route.offers[0][0]
        self.buy(item)
        before, count = self.state(), ObjectDB.objects.count()
        self.assertEqual(self.route.install(self.hub).pk, self.shop.pk)
        self.assertEqual(self.state(), before)
        self.assertEqual(ObjectDB.objects.count(), count)
        self.assertIsNone(BattleRewards.stored_attribute(self.shop, "item_replenishment"))
        self.traverse("back")
        self.finish()

    def restrictions(self):
        """No funds/bad whole quantities/resale/overstock grant no items or money."""
        from menus import item_store

        self.traverse(self.route.entrance)
        item = self.route.offers[0][0]
        self.command("store")
        self.reply("1")
        before = self.state()
        for text in (item + " 0", item + " -1", item + " 1.5", item + " 99999", "Bicycle 1"):
            self.reply(text)
            self.assertEqual(self.state(), before)
        Trainer.objects.filter(pk=self.player.trainer.pk).update(money=0)
        before = self.state()
        self.reply(item + " 1")
        self.assertEqual(self.state(), before)
        item_store.node_sell(self.player, item + " 1")
        self.assertEqual(self.state(), before)
        self.reply("back")
        self.reply("q")
        self.finish()

    def rollback(self):
        """Fault after real purchase debit/credit/stock write rolls back all resources."""
        from django.db import transaction

        self.traverse(self.route.entrance)
        item, before = self.route.offers[0][0], self.state()
        original = ShopPurchase.write_stock

        def fail_after_stock(room, stock):
            """Inject only after real stock SQL executes."""
            original(room, stock)
            raise RuntimeError("finite post-stock fixture")

        with patch.object(ShopPurchase, "write_stock", staticmethod(fail_after_stock)):
            with self.assertRaisesRegex(RuntimeError, "post-stock"):
                ShopPurchase(self.player).buy(item, 1)
        self.assertEqual(self.state(), before)
        with self.assertRaisesRegex(RuntimeError, "finite outer fixture"):
            with transaction.atomic():
                ShopPurchase(self.player).buy(item, 1)
                raise RuntimeError("finite outer fixture")
        self.assertEqual(self.state(), before)
        self.finish()

    def contention(self):
        """Competing current owners cannot both buy an authored final copy."""
        from django.db import close_old_connections

        item, _, cap = self.route.offers[0]
        self.traverse(self.route.entrance)
        for player in self.players:
            player.location = self.shop
        if cap > 1:
            ShopPurchase(self.player).buy(item, cap - 1)
        baseline = sum(player.trainer.get_item_quantity(item) for player in self.players)
        barrier = Barrier(2)

        def run(player):
            """Contend through independent database connections and production locking."""
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    ShopPurchase(player).buy(item, 1)
                    return True
                except ShopPurchaseError:
                    return False
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(run, self.players))
        self.assertEqual(sum(results), 1)
        self.assertEqual(
            sum(player.trainer.get_item_quantity(item) for player in self.players), baseline + 1
        )
        self.assertEqual(self.state()["stock"][item]["quantity"], 0)
        self.finish()

    def install_rollback(self):
        """Outer rollback removes new rooms/exits/marker; a clean retry installs once."""
        from django.db import transaction

        receipt = BattleRewards.stored_attribute(self.hub, self.route.marker)
        ObjectDB.objects.filter(
            pk__in=[receipt["room"], receipt["entrance"], receipt["return_exit"]]
        ).delete()
        self.hub.attributes.remove(self.route.marker)
        count = ObjectDB.objects.count()
        with self.assertRaisesRegex(RuntimeError, "finite install fixture"):
            with transaction.atomic():
                self.route.install(self.hub)
                raise RuntimeError("finite install fixture")
        self.assertEqual(ObjectDB.objects.count(), count)
        self.assertIsNone(BattleRewards.stored_attribute(self.hub, self.route.marker))
        self.assertIsNone(self.hub.attributes.get(self.route.marker))
        self.shop = self.route.install(self.hub)
        self.room = self.shop
        self.assertEqual(self.route.install(self.hub).pk, self.shop.pk)
        self.finish()

    def guards(self):
        """Acquisition does not bypass current target, usefulness or capacity guards."""
        item = self.route.offers[0][0]
        self.buy(item)
        before = self.state()
        self.command(
            "hold" if self.issue == 883 else "use",
            "99=" + item if self.issue == 883 else item + "=99",
        )
        self.assertEqual(self.state(), before)
        if self.issue == 881:
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(evs=[252, 0, 0, 0, 0, 0])
        if self.issue == 882:
            for slot in ActiveMoveslot.objects.filter(pokemon=self.mon):
                MovePPBoost.objects.create(
                    pokemon=self.mon,
                    move=slot.move,
                    bonus_pp=PPCapacity.for_move(slot.move.name).stages[-1],
                )
        before = self.state()
        if self.issue == 880:
            self.command("evolve", str(self.mon.pk) + " " + item)
        elif self.issue != 883:
            self.command("use", item + "=3" + ("/Water Gun" if self.issue == 879 else ""))
            if self.issue == 882:
                self.command("use", "1")
        self.assertEqual(self.state(), before)
        self.assertEqual(self.player.trainer.get_item_quantity(item), 1)
        self.finish()

    def drift(self):
        """Current source/exit conflicts are refused rather than reset or duplicated."""
        count = ObjectDB.objects.count()
        stock = self.state()["stock"]
        first = self.route.offers[0][0]
        changed = {name: dict(offer) for name, offer in stock.items()}
        changed[first]["price"] += 1
        self.room.db.store_inventory = changed
        before = self.state()
        with self.assertRaises(ValueError):
            self.route.install(self.hub)
        self.assertEqual(self.state(), before)
        self.assertEqual(ObjectDB.objects.count(), count)
        self.room.db.store_inventory = stock
        other = create_object(
            "typeclasses.rooms.FusionRoom", key="finite-conflict-" + uuid4().hex, nohome=True
        )
        with self.assertRaises(ValueError):
            self.route.install(other)
        marker = BattleRewards.stored_attribute(self.hub, self.route.marker)
        ObjectDB.objects.filter(pk=marker["return_exit"]).update(db_destination=other)
        count = ObjectDB.objects.count()
        with self.assertRaises(ValueError):
            self.route.install(self.hub)
        self.assertEqual(ObjectDB.objects.count(), count)
        self.finish()

    def coexistence(self):
        """All seven counters coexist with the original six without stock/reset collisions."""
        from pokemon.services.item_supply import ItemSupplyRoute

        created = []
        try:
            for route in (ItemSupplyRoute, *FINITE_SUPPLY_ROUTES.values()):
                room = route.install(self.hub)
                if route != self.route:
                    created.append((route, room))
            self.assertEqual(len(created), 7)
            self.buy(self.route.offers[0][0])
            before = self.state()
            for route, room in created:
                stock = BattleRewards.stored_attribute(room, "store_inventory")
                self.assertEqual(route.install(self.hub).pk, room.pk)
                self.assertEqual(BattleRewards.stored_attribute(room, "store_inventory"), stock)
                self.assertIsNone(BattleRewards.stored_attribute(room, "item_replenishment"))
            self.assertEqual(self.route.install(self.hub).pk, self.shop.pk)
            self.assertEqual(self.state(), before)
            self.finish()
        finally:
            for route, _ in created:
                receipt = BattleRewards.stored_attribute(self.hub, route.marker)
                ObjectDB.objects.filter(
                    pk__in=[receipt["room"], receipt["entrance"], receipt["return_exit"]]
                ).delete()
                self.hub.attributes.remove(route.marker)

    def start_battle(self, *, foe_species="Magikarp", foe_level=80, foe_move="Splash"):
        """Start a real wild session with only the disposable foe selection controlled."""
        self.session = acquisition.BattleSession(self.player)
        foe = acquisition.create_battle_pokemon(
            foe_species, foe_level, is_wild=True, move_names=[foe_move]
        )
        self.session._track_temp_opponent_team([foe])
        self.session._select_opponent = lambda: (
            foe,
            "Fixture " + foe_species,
            acquisition.BattleType.WILD,
            "Tagged source check",
        )
        self.session.start()
        self.session.battle.rng = random.Random(0)
        return (
            self.session.battle.participants[0].active[0],
            self.session.battle.participants[1].active[0],
        )

    def rebuild(self):
        """Reconstruct the durable production checkpoint and owned/held identities."""
        self.session._sync_active_battle_state()
        self.session._persist_turn_state()
        acquisition.battle_handler.unregister(self.session)
        for player in self.players:
            player.ndb.battle_instance = None
        self.room.ndb.battle_instances = {}
        self.session = acquisition.BattleSession.restore(self.room, self.session.battle_id)
        self.assertIsNotNone(self.session)
        return self.session.battle.participants[0].active[0]

    def manual(self, item):
        """A bought recovery copy pays for an actual +item turn and survives restore."""
        self.buy(item)
        updates = {"current_hp": 1, "status": STATUS.get(item, "")}
        if item in {"Revive", "Max Revive"}:
            updates["current_hp"] = 0
            self.native("Eevee", 1)
        if item in {"Ether", "Max Ether", "Elixir", "Max Elixir"}:
            ActiveMoveslot.objects.filter(pokemon=self.mon).update(current_pp=0)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(**updates)
        OwnedPokemon.flush_cached_instance(self.mon)
        self.mon = OwnedPokemon.objects.get(pk=self.mon.pk)
        self.start_battle()
        before, turn = self.state(), self.session.battle.turn_count
        self.command("item", item + "=3" + ("/Water Gun" if item in {"Ether", "Max Ether"} else ""))
        self.assertEqual(self.session.battle.turn_count, turn + 1, self.player.messages[-6:])
        self.assertEqual(self.player.trainer.get_item_quantity(item), 0)
        self.assertFalse(self.session.turn_state.get("error"), self.session.turn_state)
        self.assertFalse(getattr(self.session.battle, "_callback_failures", []))
        row = OwnedPokemon.objects.filter(pk=self.mon.pk).values().get()
        if item in STATUS:
            self.assertEqual(row["status"], "")
        elif self.issue == 879:
            for slot in ActiveMoveslot.objects.filter(pokemon=self.mon):
                selected = "Ether" not in item or normalize_name(slot.move.name) == "watergun"
                expected = (
                    (PPCapacity.for_move(slot.move.name).base if item.startswith("Max") else 10)
                    if selected
                    else 0
                )
                self.assertEqual(slot.current_pp, expected)
        else:
            cap = get_max_hp(self.mon)
            self.assertEqual(
                row["current_hp"],
                {
                    "Super Potion": min(cap, 61),
                    "Hyper Potion": min(cap, 121),
                    "Revive": cap // 2,
                    "Max Revive": cap,
                }[item],
            )
        self.rebuild()
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.mon.pk).values().get(), row)
        self.assertEqual(self.player.trainer.get_item_quantity(item), 0)
        self.assertEqual(self.state()["stock"], before["stock"])
        self.assertEqual(self.state()["wallet"], before["wallet"])
        self.session.end()
        self.session = None
        self.finish()

    def held(self, item):
        """Use paid berries/Sash/Choice items through actual ordinary battle turns."""
        self.buy(item)
        self.command("hold", "3=" + item)
        self.assertEqual(self.player.trainer.get_item_quantity(item), 0)
        changes = (
            {"current_hp": 1}
            if item == "Sitrus Berry"
            else {"status": "psn"} if item == "Lum Berry" else {}
        )
        if item == "Focus Sash":
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(level=5)
            OwnedPokemon.flush_cached_instance(self.mon)
            self.mon = OwnedPokemon.objects.get(pk=self.mon.pk)
            changes["current_hp"] = get_max_hp(self.mon)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(**changes)
        OwnedPokemon.flush_cached_instance(self.mon)
        self.mon = OwnedPokemon.objects.get(pk=self.mon.pk)
        holder, foe = self.start_battle(
            **(
                {"foe_species": "Rampardos", "foe_level": 100, "foe_move": "Tackle"}
                if item == "Focus Sash"
                else {}
            )
        )
        battle = self.session.battle
        before_hp, foe_hp, turn = holder.hp, foe.hp, battle.turn_count
        move = "Water Gun" if item == "Choice Specs" else "Tackle"
        with patch.object(battle, "use_move", wraps=battle.use_move) as observation:
            self.command("attack", move)
        self.assertEqual(battle.turn_count, turn + 1, self.player.messages[-6:])
        self.assertFalse(getattr(battle, "_callback_failures", []))
        actions = [
            (str(call.args[0].pokemon.model_id), call.args[0].speed)
            for call in observation.call_args_list
        ]
        detail = {
            "item": item,
            "commands": ["+hold 3=" + item, "+attack " + move],
            "hp_before": before_hp,
            "hp_after": holder.hp,
            "foe_damage": foe_hp - foe.hp,
            "executed_order": actions,
        }
        if item == "Sitrus Berry":
            self.assertEqual(holder.hp, 1 + holder.max_hp // 4)
        elif item == "Lum Berry":
            self.assertFalse(holder.status)
        elif item == "Focus Sash":
            self.assertGreater(before_hp, 1)
            self.assertEqual(holder.hp, 1)
        else:
            self.assertEqual(holder.choice_locked_move, move.lower().replace(" ", ""))
            pp = list(
                ActiveMoveslot.objects.filter(pokemon=self.mon)
                .order_by("slot")
                .values_list("current_pp", flat=True)
            )
            self.command("attack", "Tackle" if move == "Water Gun" else "Water Gun")
            self.assertEqual(battle.turn_count, turn + 1)
            self.assertEqual(
                list(
                    ActiveMoveslot.objects.filter(pokemon=self.mon)
                    .order_by("slot")
                    .values_list("current_pp", flat=True)
                ),
                pp,
            )
        restored = self.rebuild()
        self.assertEqual(restored.hp, holder.hp)
        self.session.end()
        self.session = None
        self.command("hold", "3=")
        reusable = item.startswith("Choice")
        self.assertEqual(self.player.trainer.get_item_quantity(item), int(reusable))
        self.assertEqual(
            OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("held_item", flat=True).get(),
            "",
        )
        if reusable:
            # Matched same-level/species/seed control, using actual unheld player turns.
            plain, plain_foe = self.start_battle()
            plain_hp = plain_foe.hp
            with patch.object(
                self.session.battle, "use_move", wraps=self.session.battle.use_move
            ) as plain_observation:
                self.command("attack", move)
            plain_damage = plain_hp - plain_foe.hp
            plain_actions = [
                (str(call.args[0].pokemon.model_id), call.args[0].speed)
                for call in plain_observation.call_args_list
            ]
            if item == "Choice Scarf":
                self.assertEqual(actions[0][0], holder.model_id)
                self.assertNotEqual(plain_actions[0][0], plain.model_id)
                boosted_speed = next(
                    speed for identifier, speed in actions if identifier == holder.model_id
                )
                plain_speed = next(
                    speed for identifier, speed in plain_actions if identifier == plain.model_id
                )
                self.assertEqual(boosted_speed, plain_speed * 3 // 2)
            else:
                self.assertGreater(detail["foe_damage"], plain_damage)
            detail.update(plain_damage=plain_damage, plain_executed_order=plain_actions)
            self.session.end()
            self.session = None
        EVIDENCE.append({"issue": self.issue, "label": "purchased-held-item-battle", **detail})
        self.finish()


def add_case(name, issue, method, item=None):
    """Expose each exact offer and each source-specific control as its own case."""

    def test(self):
        """Execute this accepted finite counter's ordinary route or transaction guard."""
        getattr(self, method)(item) if item else getattr(self, method)()

    case_type = CASE_TYPES.setdefault(
        issue, type("FiniteSource" + str(issue), (FiniteSupplyCases,), {"issue": issue})
    )
    setattr(case_type, "test_" + name, test)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        acquisition.load_runtime()
        import evennia
        from evennia.commands.command import Command

        with patch.object(evennia, "Command", Command):
            from commands.player import cmd_battle_item
        acquisition.COMMANDS["item"] = (cmd_battle_item, cmd_battle_item.CmdBattleItem)
        from evennia.objects.models import ObjectDB

        six_supply.ObjectDB = ObjectDB
        from evennia.utils.create import create_object
        from django.contrib.contenttypes.models import ContentType

        ContentType.objects.get_for_model(ObjectDB)
        from pokemon.helpers.pokemon_helpers import get_max_hp
        from pokemon.names import normalize_name
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot, MovePPBoost
        from pokemon.models.trainer import Trainer
        from pokemon.services.battle_rewards import BattleRewards
        from pokemon.services.finite_item_supply import FINITE_SUPPLY_ROUTES
        from pokemon.services.item_shop import ShopPurchase, ShopPurchaseError
        from pokemon.services.placement import PlacementService
        from pokemon.services.pp_capacity import PPCapacity

        CASE_TYPES = {}
        for issue, route in FINITE_SUPPLY_ROUTES.items():
            if issue != 883:
                for name in route.names:
                    add_case(
                        "field_" + "".join(c for c in name if c.isalnum()), issue, "field", name
                    )
                    if issue in {877, 878, 879}:
                        add_case(
                            "manual_" + "".join(c for c in name if c.isalnum()),
                            issue,
                            "manual",
                            name,
                        )
            else:
                for name in route.names:
                    add_case("held_" + "".join(c for c in name if c.isalnum()), issue, "held", name)
            for method in (
                "retry",
                "restrictions",
                "rollback",
                "contention",
                "install_rollback",
                "guards",
                "drift",
            ):
                add_case(method, issue, method)
        add_case("coexistence", 877, "coexistence")
        suite = unittest.TestSuite(
            unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in CASE_TYPES.values()
        )
        try:
            result = unittest.TextTestRunner(verbosity=2).run(suite)
        finally:
            if os.environ.get("PF2_FINITE_SUPPLY_EVIDENCE"):
                Path(os.environ["PF2_FINITE_SUPPLY_EVIDENCE"]).write_text(
                    json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8"
                )
        raise SystemExit(not result.wasSuccessful())

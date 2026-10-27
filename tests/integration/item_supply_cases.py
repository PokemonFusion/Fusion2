"""Discover, purchase and use all six authored supplies on disposable PostgreSQL."""

import json
import os
from pathlib import Path
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
import item_availability_cases as acquisition

EVIDENCE = []


class ItemSupplyCases(unittest.TestCase):
    """Separate authorized content setup from ordinary exit/menu/effect operations."""

    native = acquisition.AcquisitionCases.native
    state = acquisition.AcquisitionCases.state
    command = acquisition.AcquisitionCases.command
    reply = acquisition.AcquisitionCases.reply
    field = acquisition.AcquisitionCases.field
    evolve = acquisition.AcquisitionCases.evolve
    record_effect = acquisition.AcquisitionCases.record_effect

    def setUp(self):
        """Author one tagged disposable public hub, then use the opt-in installer."""
        acquisition.AcquisitionCases.setUp(self)
        self.hub = create_object("typeclasses.rooms.FusionRoom", key="supply-hub-" + uuid4().hex, nohome=True)
        self.hub.db.desc = "A public test hub with a clearly labeled supplies exit."
        self.shop = ItemSupplyRoute.install(self.hub)
        self.room = self.shop
        for player in self.players:
            player.location = self.hub
            ObjectDB.objects.filter(pk=player.pk).update(db_location_id=self.hub.pk)
            player.move_to = lambda destination, *args, _player=player, **kwargs: self.move(_player, destination)

    def tearDown(self):
        """Close only fixture sessions and remove this disposable route's SQL objects."""
        acquisition.AcquisitionCases.tearDown(self)
        receipt = BattleRewards.stored_attribute(self.hub, ItemSupplyRoute.marker)
        if receipt:
            ObjectDB.objects.filter(pk__in=[receipt["room"], receipt["entrance"], receipt["return_exit"]]).delete()
        self.hub.attributes.remove(ItemSupplyRoute.marker)

    def move(self, player, destination):
        """Delegate actual traversal persistence while adapting transport location."""
        moved = player.character.move_to(destination, quiet=True, move_hooks=False)
        if moved:
            player.location = destination
        return moved

    def traverse(self, key):
        """Execute the real authored Exit command, including its normal traverse lock."""
        exit_object = ObjectDB.objects.get(db_location_id=self.player.location.pk, db_key=key)
        command = exit_object.exit_command()
        command.caller, command.obj, command.args = self.player, exit_object, ""
        command.func()
        self.assertEqual(ObjectDB.objects.filter(pk=self.player.pk).values_list("db_location_id", flat=True).get(), exit_object.db_destination_id)
        return exit_object

    def buy(self, item, **kwargs):
        """Buy only existing authored stock; never replace it with a one-item fixture."""
        if self.player.location.pk == self.hub.pk:
            self.traverse("supplies")
        before = self.state()
        offer = dict(before["stock"][item])
        self.command("store")
        self.reply("1")
        self.reply(item + " 1")
        self.reply("back")
        self.reply("q")
        self.assertEqual(self.player.trainer.get_item_quantity(item), 1)
        self.assertEqual(self.state()["wallet"], before["wallet"] - offer["price"])
        self.assertEqual(self.state()["stock"][item]["quantity"], offer["quantity"] - 1)
        EVIDENCE.append({"label": "authored-supply-purchase", "item": item, "before": before,
                         "after": self.state(), "source_room": self.shop.pk})

    def test_potion_route(self):
        """Ordinary supplies exit -> shop -> bag -> useful Potion -> reload."""
        self.field("Potion")
        self.traverse("back")

    def test_oran_route(self):
        """The same real six-offer source supports existing field berries."""
        self.field("Oran Berry")

    def test_fresh_water_route(self):
        """Existing recovery food works after actual authored stock purchase."""
        self.field("Fresh Water")

    def test_fire_stone_route(self):
        """Purchase and explicit normal evolution preserve the configured source."""
        self.evolve("Fire Stone")

    def test_leftovers_route(self):
        """Buy/equip, real battle residual healing, reload and return the reusable item."""
        acquisition.AcquisitionCases.test_shop_to_leftovers_battle_healing_and_reload(self)

    def test_smoke_ball_route(self):
        """Buy/equip and ordinary flee/rebuild/return use the authored offer."""
        acquisition.AcquisitionCases.test_shop_to_held_escape_and_return_to_bag(self)

    def test_reinstall_preserves_sold_stock_and_exact_links(self):
        """Idempotency returns the existing location, never replenishing sold copies."""
        self.buy("Potion")
        before, count = self.state(), ObjectDB.objects.count()
        self.assertEqual(ItemSupplyRoute.install(self.hub).pk, self.shop.pk)
        self.assertEqual(self.state(), before)
        self.assertEqual(ObjectDB.objects.count(), count)
        self.assertEqual(set(before["stock"]), ItemSupplyRoute.names)
        self.assertIn("+store", self.shop.db.desc)
        self.traverse("back")
        self.assertEqual(self.player.location.pk, self.hub.pk)

    def test_conflicting_hub_and_damaged_exit_fail_without_duplicates(self):
        """An explicit conflict requires review instead of another global source."""
        other = create_object("typeclasses.rooms.FusionRoom", key="supply-other-" + uuid4().hex, nohome=True)
        before = ObjectDB.objects.count()
        with self.assertRaises(ValueError):
            ItemSupplyRoute.install(other)
        self.assertEqual(ObjectDB.objects.count(), before)
        receipt = BattleRewards.stored_attribute(self.hub, ItemSupplyRoute.marker)
        ObjectDB.objects.filter(pk=receipt["return_exit"]).update(db_destination_id=other.pk)
        with self.assertRaises(ValueError):
            ItemSupplyRoute.install(self.hub)
        self.assertEqual(ObjectDB.objects.count(), before)

    def test_buy_only_empty_and_funds_controls(self):
        """The bounded source does not inherit legacy player-sale stock mutation."""
        from menus import item_store

        self.traverse("supplies")
        text, options = item_store.node_start(self.player)
        self.assertNotIn("Sell items", str(options))
        before = self.state()
        item_store.node_sell(self.player, "Potion 1")
        self.assertEqual(self.state(), before)
        self.command("store")
        self.reply("1")
        self.reply("Potion 999")
        self.assertEqual(self.state(), before)
        Trainer.objects.filter(pk=self.player.trainer.pk).update(money=0)
        before = self.state()
        self.reply("Smoke Ball 1")
        self.assertEqual(self.state(), before)

    def test_concurrent_install_returns_one_source_without_reset(self):
        """A global transaction lock protects against simultaneous setup requests."""
        from django.db import close_old_connections

        barrier = Barrier(2)

        def run(_):
            """Use independent database connections for the idempotent installer."""
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return ItemSupplyRoute.install(self.hub).pk
            finally:
                close_old_connections()

        before = self.state()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(run, range(2)))
        self.assertEqual(results, [self.shop.pk, self.shop.pk])
        self.assertEqual(self.state(), before)

    def test_setup_failure_rolls_back_then_clean_retry_installs_once(self):
        """A fault after real room creation leaves no partial source or hub receipt."""
        receipt = BattleRewards.stored_attribute(self.hub, ItemSupplyRoute.marker)
        ObjectDB.objects.filter(pk__in=[receipt["room"], receipt["entrance"], receipt["return_exit"]]).delete()
        self.hub.attributes.remove(ItemSupplyRoute.marker)
        count = ObjectDB.objects.count()
        original = create_object

        def fail_after_create(*args, **kwargs):
            """Execute real authored-room SQL before failing inside the installer."""
            original(*args, **kwargs)
            raise RuntimeError("supply setup fixture")

        with patch("evennia.utils.create.create_object", fail_after_create):
            with self.assertRaisesRegex(RuntimeError, "supply setup fixture"):
                ItemSupplyRoute.install(self.hub)
        self.assertEqual(ObjectDB.objects.count(), count)
        self.assertIsNone(BattleRewards.stored_attribute(self.hub, ItemSupplyRoute.marker))
        self.shop = ItemSupplyRoute.install(self.hub)
        self.room = self.shop
        self.assertEqual(ItemSupplyRoute.install(self.hub).pk, self.shop.pk)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        acquisition.load_runtime()
        from evennia.objects.models import ObjectDB
        from evennia.utils.create import create_object
        from django.contrib.contenttypes.models import ContentType
        ContentType.objects.get_for_model(ObjectDB)
        from pokemon.models.trainer import Trainer
        from pokemon.services.battle_rewards import BattleRewards
        from pokemon.services.item_supply import ItemSupplyRoute

        try:
            result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ItemSupplyCases))
        finally:
            if os.environ.get("PF2_ITEM_SUPPLY_EVIDENCE"):
                Path(os.environ["PF2_ITEM_SUPPLY_EVIDENCE"]).write_text(json.dumps(EVIDENCE + acquisition.EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())

"""Atomic ordinary shop menu purchases on disposable PostgreSQL."""

import json
import os
from pathlib import Path
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import item_availability_cases as acquisition

EVIDENCE = []


class ShopPurchaseCases(unittest.TestCase):
    """Reuse acquisition transport while keeping these commerce assertions independent."""

    setUp = acquisition.AcquisitionCases.setUp
    tearDown = acquisition.AcquisitionCases.tearDown
    native = acquisition.AcquisitionCases.native
    state = acquisition.AcquisitionCases.state
    command = acquisition.AcquisitionCases.command
    reply = acquisition.AcquisitionCases.reply

    def stock(self, quantity=1, price=300):
        """Author exactly one disposable offer before invoking normal menus."""
        self.room.db.store_inventory = {"Potion": {"price": price, "quantity": quantity}}

    def buy(self, text="Potion 1"):
        """Submit real +store and bound Evennia menu input."""
        self.command("store")
        self.reply("1")
        self.reply(text)
        self.reply("back")
        self.reply("q")

    def test_menu_purchase_reload_and_legal_repeat(self):
        """Each deliberate purchase spends exact money/stock and credits one copy."""
        self.stock(2)
        before = self.state()
        self.buy()
        self.buy()
        self.assertEqual(self.state()["wallet"], before["wallet"] - 600)
        self.assertEqual(self.state()["stock"]["Potion"]["quantity"], 0)
        self.assertEqual(self.player.trainer.get_item_quantity("Potion"), 2)
        EVIDENCE.append({"label": "normal-menu-purchase", "before": before, "after": self.state()})

    def test_post_credit_failure_rolls_back_all_sql_and_caches(self):
        """Retain the original confirmed failure boundary after real item credit."""
        self.stock()
        before = self.state()
        original = Trainer.add_item

        def fail_after_credit(trainer, *args):
            """Inject only after production inventory SQL has executed."""
            original(trainer, *args)
            raise RuntimeError("post-credit fixture")

        with patch.object(Trainer, "add_item", fail_after_credit):
            self.buy()
        self.assertEqual(self.state(), before)
        self.assertEqual(dict(self.player.db.inventory or {}), {})
        self.assertEqual(self.player.trainer.money, before["wallet"])
        self.assertFalse(any("You purchase" in str(text) for text in self.player.messages))

    def test_post_stock_failure_rolls_back_all_resources(self):
        """Real stock UPDATE followed by a fault cannot leave uncommitted caches."""
        self.stock()
        before = self.state()
        original = ShopPurchase.write_stock

        def fail_after_stock(room, store):
            """Execute the real Attribute SQL before failing."""
            original(room, store)
            raise RuntimeError("post-stock fixture")

        with patch.object(ShopPurchase, "write_stock", fail_after_stock):
            self.buy()
        self.assertEqual(self.state(), before)
        self.assertEqual(self.room.db.store_inventory["Potion"]["quantity"], 1)

    def test_partial_money_failure_rolls_back(self):
        """A debit that returns false after writing cannot spend the wallet."""
        self.stock()
        before = self.state()
        original = Trainer.spend_money

        def partial(trainer, amount):
            """Fail only after the real money save."""
            original(trainer, amount)
            return False

        with patch.object(Trainer, "spend_money", partial):
            self.buy()
        self.assertEqual(self.state(), before)
        self.assertEqual(self.player.trainer.money, before["wallet"])

    def test_parent_rollback_leaves_no_success_or_shared_stock(self):
        """A caller-owned transaction cannot publish success or poison room caches."""
        from django.db import transaction

        self.stock()
        before = self.state()
        with self.assertRaisesRegex(RuntimeError, "outer rollback"):
            with transaction.atomic():
                ShopPurchase(self.player).buy("Potion", 1)
                self.assertEqual(self.room.db.store_inventory["Potion"]["quantity"], 1)
                self.assertFalse(any("You purchase" in str(text) for text in self.player.messages))
                raise RuntimeError("outer rollback")
        self.assertEqual(self.state(), before)
        self.assertEqual(self.room.db.store_inventory["Potion"]["quantity"], 1)

    def test_invalid_offer_funds_quantity_and_disabled_shop(self):
        """Every refusal preserves exact SQL rather than accepting free malformed offers."""
        for price, quantity, amount in ((-1, 1, 1), (True, 1, 1), (300, True, 1),
                                         (300, 0, 1), (300000, 1, 1), (300, 1, 2)):
            self.stock(quantity, price)
            before = self.state()
            self.buy(f"Potion {amount}")
            self.assertEqual(self.state(), before)
        self.stock()
        for amount in (0, -1, True, "1"):
            before = self.state()
            with self.assertRaises(ShopPurchaseError):
                ShopPurchase(self.player).buy("Potion", amount)
            self.assertEqual(self.state(), before)
        self.room.db.is_item_shop = False
        with self.assertRaises(ShopPurchaseError):
            ShopPurchase(self.player).buy("Potion", 1)

    def race(self, players):
        """Contend for the same final stock through independent SQL connections."""
        from django.db import close_old_connections

        barrier = Barrier(len(players))

        def run(player):
            """Release worker connections and retain only expected stock refusals."""
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    ShopPurchase(player).buy("Potion", 1)
                    return True
                except ShopPurchaseError:
                    return False
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=len(players)) as pool:
            return list(pool.map(run, players))

    def test_two_buyers_share_last_stock(self):
        """Two ordinary owners cannot both acquire the last item."""
        self.stock()
        for player in self.players:
            Trainer.objects.filter(pk=player.trainer.pk).update(money=1000)
        results = self.race(self.players)
        self.assertEqual(sum(results), 1)
        self.assertEqual(sum(player.trainer.get_item_quantity("Potion") for player in self.players), 1)
        self.assertEqual(sum(Trainer.objects.filter(pk=player.trainer.pk).values_list("money", flat=True).get() for player in self.players), 1700)
        self.assertEqual(self.state()["stock"]["Potion"]["quantity"], 0)
        EVIDENCE.append({"label": "two-buyer-contention", "successes": results, "after": self.state()})

    def test_same_buyer_competing_purchases_share_wallet(self):
        """Two available copies do not let a buyer spend the same funds twice."""
        self.stock(2)
        Trainer.objects.filter(pk=self.player.trainer.pk).update(money=300)
        self.assertEqual(sum(self.race([self.player, self.player])), 1)
        self.assertEqual(self.player.trainer.get_item_quantity("Potion"), 1)
        self.assertEqual(self.state()["wallet"], 0)
        self.assertEqual(self.state()["stock"]["Potion"]["quantity"], 1)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        acquisition.load_runtime()
        from pokemon.models.trainer import Trainer
        from pokemon.services.item_shop import ShopPurchase, ShopPurchaseError

        try:
            result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ShopPurchaseCases))
        finally:
            if os.environ.get("PF2_SHOP_PURCHASE_EVIDENCE"):
                Path(os.environ["PF2_SHOP_PURCHASE_EVIDENCE"]).write_text(json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())

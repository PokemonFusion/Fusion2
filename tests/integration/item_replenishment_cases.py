"""Operator refill and ordinary +store/+use checks on disposable PostgreSQL.

No migration, live socket, permanent stock or existing human rows are involved.
The clock seam only advances this suite's deterministic UTC fixture.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
import item_availability_cases as acquisition

EVIDENCE = []


class ReplenishmentCases(unittest.TestCase):
    """Use real SQL, production account checks, purchases, medicine and caches."""

    tearDown = acquisition.AcquisitionCases.tearDown
    native = acquisition.AcquisitionCases.native
    player_state = acquisition.AcquisitionCases.state
    command = acquisition.AcquisitionCases.command
    reply = acquisition.AcquisitionCases.reply

    def setUp(self):
        """Prepare fresh tagged full stock and a separate real operator account."""
        acquisition.AcquisitionCases.setUp(self)
        self.shop = ObjectDB.objects.get(pk=self.room.pk)
        self.room.db.store_buy_only = True
        self.policy = ReplenishmentPolicy(
            "qa-refill-876", 1, (("Potion", 300, 2), ("Oran Berry", 80, 3))
        )
        self.room.db.store_inventory = self.policy.vector()
        self.actor = AccountDB.objects.create(
            username="refill-operator-" + uuid4().hex, is_active=True, is_superuser=False
        )
        self.actor.permissions.add("Builder")
        self.start = datetime(2026, 10, 25, 23, 59, tzinfo=timezone.utc)
        self.time = patch.object(ItemReplenishment, "clock", return_value=self.start)
        self.clock = self.time.start()
        self.addCleanup(self.time.stop)
        self.initial = ItemReplenishment.configure(self.shop, self.policy, self.actor)
        self.request = str(uuid4())
        self.test_before = self.state()
        self.addCleanup(self.record)

    def state(self):
        """Reload SQL stock, ledger, wallet, bag, owned rows and source caches."""
        state = self.player_state()
        state["marker"] = ItemReplenishment.read(self.shop, ItemReplenishment.marker)
        keys = (
            self.shop.db_attributes.filter(db_category=ItemReplenishment.category)
            .order_by("db_key")
            .values_list("db_key", flat=True)
        )
        state["receipts"] = [
            ItemReplenishment.read(self.shop, key, category=ItemReplenishment.category)
            for key in keys
        ]
        return state

    def record(self):
        """Retain a per-case final SQL observation and ordinary client output."""
        EVIDENCE.append(
            {
                "case": self.id().split(".")[-1],
                "before": self.test_before,
                "after": self.state(),
                "messages": self.player.messages,
                "setup": "Tagged disposable stock/operator/wallet/native target; no item grants",
                "evidence_kind": "production commands with captured transport and fresh SQL",
            }
        )

    def buy(self, text="Potion 1"):
        """Use the actual ordinary command and bound EvMenu input path."""
        self.command("store")
        self.reply("1")
        self.reply(text)
        self.reply("back")
        self.reply("q")

    def eligible(self, days=1):
        """Advance only the controlled server-clock seam by real UTC duration."""
        self.clock.return_value = self.start + timedelta(days=days)

    def refill(self, request=None, actor=None, policy=None):
        """Invoke the separate operator API with its exact source revision."""
        return ItemReplenishment.refill(
            self.shop, policy or self.policy, actor or self.actor, request or self.request
        )

    def assert_refused(self, pattern, **kwargs):
        """A rejected operator request must preserve every observed SQL resource."""
        before = self.state()
        with self.assertRaisesRegex(ReplenishmentError, pattern):
            self.refill(**kwargs)
        self.assertEqual(self.state(), before)

    def test_ordinary_buy_empty_refill_buy_use_and_reload(self):
        """Player buys the last copies, observes empty stock, then uses paid stock."""
        self.buy("Potion 2")
        before = self.state()
        self.buy()
        self.assertEqual(self.state(), before)
        self.eligible()
        receipt = self.refill()
        self.assertEqual(receipt["delta"], {"Potion": 2, "Oran Berry": 0})
        self.assertEqual(self.state()["wallet"], before["wallet"])
        self.assertEqual(self.state()["bag"], before["bag"])
        self.buy()
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=1)
        before = self.state()
        self.command("inventory")
        self.command("use", "Potion=3")
        self.assertEqual(self.player.trainer.get_item_quantity("Potion"), 2)
        row = OwnedPokemon.objects.filter(pk=self.mon.pk).values("current_hp").get()
        self.assertEqual(row["current_hp"], 21)
        self.assertEqual(self.state()["wallet"], before["wallet"])
        self.assertEqual(self.state()["stock"], before["stock"])
        self.shop.attributes.reset_cache()
        ObjectDB.flush_cached_instance(self.shop)
        self.shop = ObjectDB.objects.get(pk=self.shop.pk)
        self.assertEqual(
            ItemReplenishment.read(
                self.shop, receipt["request"], category=ItemReplenishment.category
            ),
            receipt,
        )
        self.assertEqual(self.state()["marker"]["sequence"], 1)

    def test_exact_boundary_midnight_and_microsecond_early(self):
        """Midnight and 23:59:59.999999 are too early; exact 24h is eligible."""
        self.buy()
        for offset in (timedelta(minutes=2), timedelta(hours=24, microseconds=-1)):
            self.clock.return_value = self.start + offset
            self.assert_refused("not eligible")
        self.eligible()
        self.assertEqual(self.refill()["delta"]["Potion"], 1)

    def test_next_interval_begins_at_actual_committed_refill(self):
        """Late refills give no accumulated debt and no next-midnight shortcut."""
        self.buy()
        self.eligible(10)
        first = self.refill()
        self.assertEqual(first["sequence"], 1)
        self.buy()
        self.clock.return_value += timedelta(hours=23, minutes=59)
        self.assert_refused("not eligible", request=str(uuid4()))
        self.clock.return_value += timedelta(minutes=1)
        second = self.refill(request=str(uuid4()))
        self.assertEqual(second["sequence"], 2)
        self.assertEqual(second["delta"]["Potion"], 1)

    def test_full_stock_noop_does_not_consume_window_or_request(self):
        """A no-effect call grants no credit, receipt, sequence or cooldown."""
        self.eligible()
        before = self.state()
        self.assertIsNone(self.refill())
        self.assertEqual(self.state(), before)
        self.buy()
        self.assertEqual(self.refill()["delta"]["Potion"], 1)

    def test_duplicate_request_after_purchase_and_later_refill(self):
        """Even an old replay returns its historical receipt without adding stock."""
        self.buy()
        self.eligible()
        first = self.refill()
        self.buy()
        before = self.state()
        self.assertEqual(self.refill(), first)
        self.assertEqual(self.state(), before)
        self.eligible(2)
        self.refill(request=str(uuid4()))
        self.buy()
        before = self.state()
        self.assertEqual(self.refill(), first)
        self.assertEqual(self.state(), before)

    def test_different_request_cannot_refill_same_window(self):
        """A fresh UUID is not a way around the source-wide elapsed interval."""
        self.buy()
        self.eligible()
        self.refill()
        self.buy()
        self.assert_refused("not eligible", request=str(uuid4()))

    def test_clock_rollback_before_initial_and_after_refill(self):
        """Clock rollback refuses both fresh and replayed requests without writes."""
        self.buy()
        self.clock.return_value = self.start - timedelta(microseconds=1)
        self.assert_refused("backwards")
        self.eligible()
        self.refill()
        self.clock.return_value -= timedelta(microseconds=1)
        self.assert_refused("backwards")
        self.assert_refused("backwards", request=str(uuid4()))

    def test_configure_retry_after_purchase_preserves_initial_caps(self):
        """Retries never reset stock, clock, instance or durable receipts."""
        self.buy()
        before = self.state()
        self.eligible()
        self.assertEqual(
            ItemReplenishment.configure(self.shop, self.policy, self.actor), self.initial
        )
        self.assertEqual(self.state(), before)
        self.refill()
        before = self.state()
        ItemReplenishment.configure(self.shop, self.policy, self.actor)
        self.assertEqual(self.state(), before)

    def test_no_optin_is_not_a_refill_source(self):
        """An ordinary finite counter is not implicitly replenishable."""
        self.shop.attributes.remove(ItemReplenishment.marker)
        self.eligible()
        self.assert_refused("opt-in")

    def test_sold_counter_cannot_bootstrap_new_caps(self):
        """Only exact untouched initial stock may opt in to a reviewed manifest."""
        self.shop.attributes.remove(ItemReplenishment.marker)
        self.buy()
        before = self.state()
        with self.assertRaisesRegex(ReplenishmentError, "initial stock"):
            ItemReplenishment.configure(self.shop, self.policy, self.actor)
        self.assertEqual(self.state(), before)

    def test_policy_drift_is_refused(self):
        """New source/version/price/cap/item identities require separate review."""
        self.buy()
        self.eligible()
        for policy in (
            ReplenishmentPolicy("qa-other-876", 1, self.policy.offers),
            ReplenishmentPolicy(self.policy.source, 2, self.policy.offers),
            ReplenishmentPolicy(self.policy.source, 1, (("Potion", 301, 2), ("Oran Berry", 80, 3))),
            ReplenishmentPolicy(self.policy.source, 1, (("Potion", 300, 3), ("Oran Berry", 80, 3))),
            ReplenishmentPolicy(self.policy.source, 1, (("Potion", 300, 2),)),
        ):
            self.assert_refused("opt-in|drifted", policy=policy)

    def test_stock_and_flags_drift_are_refused(self):
        """Malformed prices/counts, additions, resale and disabled sources fail closed."""
        self.eligible()
        for name, value in (
            ("price", True),
            ("price", 301),
            ("quantity", True),
            ("quantity", -1),
            ("quantity", 3),
            ("quantity", None),
        ):
            stock = self.policy.vector()
            stock["Potion"][name] = value
            self.room.db.store_inventory = stock
            self.assert_refused("drifted")
        for stock in ({}, {**self.policy.vector(), "Bicycle": {"price": 1, "quantity": 1}}):
            self.room.db.store_inventory = stock
            self.assert_refused("drifted")
        self.room.db.store_inventory = self.policy.vector()
        for key in ("store_buy_only", "is_item_shop"):
            self.room.attributes.add(key, False)
            self.assert_refused("buy-only")
            self.room.attributes.add(key, True)

    def test_legacy_supply_corner_stays_excluded(self):
        """Renaming an operator policy cannot opt the original tagged source in."""
        self.shop.tags.add("nonplot-item-supply-v1", category="item_supply")
        self.eligible()
        self.assert_refused("separately reviewed")
        before = self.state()
        with self.assertRaisesRegex(ReplenishmentError, "separately reviewed"):
            ItemReplenishment.configure(self.shop, self.policy, self.actor)
        self.assertEqual(self.state(), before)

    def test_current_account_permissions_not_stale_flags(self):
        """Cached Builder/superuser flags cannot survive SQL revocation/deactivation."""
        self.buy()
        self.eligible()
        self.actor.permissions.all()
        self.actor.permissions.remove("Builder")
        self.actor.is_superuser = True
        self.assert_refused("Builder")
        self.actor.permissions.add("Admin")
        AccountDB.objects.filter(pk=self.actor.pk).update(is_active=False)
        self.assert_refused("Builder")
        AccountDB.objects.filter(pk=self.actor.pk).update(is_active=True, db_is_bot=True)
        self.assert_refused("Builder")
        AccountDB.objects.filter(pk=self.actor.pk).update(db_is_bot=False)
        self.assertIsNotNone(self.refill())

    def test_fake_actor_or_character_does_not_authorize(self):
        """Neither a character nor a client object with an account-like ID may refill."""
        self.eligible()
        for actor in (
            self.player.character,
            SimpleNamespace(pk=self.actor.pk, is_superuser=True),
            AccountDB(username="unsaved-operator", is_superuser=True),
        ):
            self.assert_refused("Builder", actor=actor)

    def test_cached_builder_tag_cannot_survive_direct_sql_revocation(self):
        """Permission-cache contents cannot replace the real current account tags."""
        self.buy()
        self.eligible()
        self.assertTrue(self.actor.permissions.check("Builder"))
        self.actor.db_tags.clear()
        self.assert_refused("Builder")

    def test_request_uuid_and_actor_identity(self):
        """Requests must be unique UUIDs; a replay cannot impersonate its actor."""
        self.buy()
        self.eligible()
        for request in ("bad-id", "123", object()):
            self.assert_refused("UUID", request=request)
        self.refill()
        other = AccountDB.objects.create(username="refill-other-" + uuid4().hex, is_superuser=True)
        self.assert_refused("different operator", actor=other)

    def test_fault_after_stock_rolls_back_stock_and_ledger(self):
        """A real stock SQL write followed by a fault grants no refill."""
        self.buy()
        self.eligible()
        before = self.state()
        original = ShopPurchase.write_stock

        def fault(room, stock):
            """Inject only after the real production stock write."""
            original(room, stock)
            raise RuntimeError("post-stock fixture")

        with patch.object(ShopPurchase, "write_stock", fault):
            with self.assertRaisesRegex(RuntimeError, "post-stock"):
                self.refill()
        self.assertEqual(self.state(), before)
        self.assertEqual(self.room.db.store_inventory["Potion"]["quantity"], 1)
        self.assertIsNotNone(self.refill())

    def test_fault_after_receipt_rolls_back_stock_and_ledger(self):
        """A persisted receipt followed by failure rolls back the entire action."""
        self.buy()
        self.eligible()
        before = self.state()
        original = ItemReplenishment.write

        def fault(room, key, value, **kwargs):
            """Fail after the real receipt INSERT and relation creation."""
            original(room, key, value, **kwargs)
            if kwargs.get("category") == ItemReplenishment.category:
                raise RuntimeError("post-receipt fixture")

        with patch.object(ItemReplenishment, "write", fault):
            with self.assertRaisesRegex(RuntimeError, "post-receipt"):
                self.refill()
        self.assertEqual(self.state(), before)
        self.assertIsNotNone(self.refill())

    def test_outer_refill_rollback_discards_cache_and_request(self):
        """Caller-owned rollback leaves no stock, sequence or false replay receipt."""
        from django.db import transaction

        self.buy()
        self.eligible()
        before = self.state()
        # Prime both Attribute caches before the nested transaction.
        self.assertEqual(self.shop.db.item_replenishment["sequence"], 0)
        self.assertEqual(self.shop.db.store_inventory["Potion"]["quantity"], 1)
        with self.assertRaisesRegex(RuntimeError, "outer fixture"):
            with transaction.atomic():
                self.refill()
                self.assertEqual(self.shop.db.store_inventory["Potion"]["quantity"], 1)
                raise RuntimeError("outer fixture")
        self.assertEqual(self.state(), before)
        self.assertEqual(self.shop.db.item_replenishment["sequence"], 0)
        self.assertEqual(self.refill()["sequence"], 1)

    def test_outer_configure_rollback_can_retry_without_ghost_marker(self):
        """New Attribute creation is not visible through a rolled-back relation."""
        from django.db import transaction

        self.shop.attributes.remove(ItemReplenishment.marker)
        before = self.state()
        with self.assertRaisesRegex(RuntimeError, "outer setup fixture"):
            with transaction.atomic():
                ItemReplenishment.configure(self.shop, self.policy, self.actor)
                raise RuntimeError("outer setup fixture")
        self.assertEqual(self.state(), before)
        self.assertIsNone(self.shop.db.item_replenishment)
        self.assertEqual(
            ItemReplenishment.configure(self.shop, self.policy, self.actor)["sequence"], 0
        )

    def test_outer_commit_refreshes_normal_attribute_views(self):
        """A successful outer commit publishes the exact stock and latest marker."""
        from django.db import transaction

        self.buy()
        self.eligible()
        self.assertEqual(self.shop.db.store_inventory["Potion"]["quantity"], 1)
        with transaction.atomic():
            receipt = self.refill()
        self.assertEqual(self.shop.db.store_inventory["Potion"]["quantity"], 2)
        self.assertEqual(self.shop.db.item_replenishment["request"], receipt["request"])

    def test_duplicate_marker_requires_review(self):
        """Ambiguous duplicate Attributes cannot pick a favorable cooldown."""
        from evennia.typeclasses.models import Attribute
        from evennia.utils.dbserialize import to_pickle

        self.eligible()
        attribute = Attribute.objects.create(
            db_key=ItemReplenishment.marker, db_model="objectdb", db_value=to_pickle(self.initial)
        )
        self.shop.db_attributes.add(attribute)
        # Read ambiguity itself is the refusal; inspect the immutable stock directly.
        before = self.player_state()
        with self.assertRaisesRegex(ReplenishmentError, "Duplicate"):
            self.refill()
        self.assertEqual(self.player_state(), before)
        self.shop.db_attributes.remove(attribute)

    def test_receipt_or_marker_drift_is_refused(self):
        """Missing/modified history or cross-room markers cannot reset the window."""
        self.buy()
        self.eligible()
        receipt = self.refill()
        original = ItemReplenishment.read(self.shop, ItemReplenishment.marker)
        for key, value in (
            ("room", self.shop.pk + 10000),
            ("sequence", -1),
            ("instance", "bad"),
            ("last", "2026-10-25"),
        ):
            state = {**original, key: value}
            ItemReplenishment.write(self.shop, ItemReplenishment.marker, state)
            self.assert_refused("review|opt-in")
        ItemReplenishment.write(self.shop, ItemReplenishment.marker, original)
        ItemReplenishment.write(
            self.shop,
            self.request,
            {**receipt, "delta": {"Potion": 999}},
            category=ItemReplenishment.category,
        )
        self.assert_refused("receipt")
        self.shop.attributes.remove(self.request, category=ItemReplenishment.category)
        self.assert_refused("receipt")

    def race(self, actions):
        """Run contending operations on independent guarded SQL connections."""
        from django.db import close_old_connections

        barrier = Barrier(len(actions))

        def run(action):
            """Retain expected service refusals, propagate unexpected failures."""
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    return action()
                except (ReplenishmentError, ShopPurchaseError) as error:
                    return str(error)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            return list(pool.map(run, actions))

    def test_concurrent_same_request_has_one_receipt_and_delta(self):
        """Two operator retries return one identical committed result."""
        self.buy()
        self.eligible()
        results = self.race([self.refill, self.refill])
        self.assertIsInstance(results[0], dict)
        self.assertEqual(results[0], results[1])
        self.assertEqual(len(self.state()["receipts"]), 1)
        self.assertEqual(self.state()["stock"], self.policy.vector())

    def test_concurrent_different_requests_have_one_refill(self):
        """Concurrent UUIDs still share the one source-wide interval."""
        self.buy()
        self.eligible()
        results = self.race([self.refill, lambda: self.refill(request=str(uuid4()))])
        self.assertEqual(sum(isinstance(result, dict) for result in results), 1)
        self.assertEqual(len(self.state()["receipts"]), 1)
        self.assertTrue(any("not eligible" in str(result) for result in results))

    def test_purchase_and_refill_serialize_without_lost_stock(self):
        """Either legal order conserves purchased copies and the recorded stock delta."""
        self.buy()
        self.eligible()
        before = self.state()
        results = self.race([self.refill, lambda: ShopPurchase(self.player).buy("Potion", 1)])
        receipt = next(result for result in results if isinstance(result, dict))
        self.assertFalse(any(isinstance(result, str) for result in results))
        after = self.state()
        self.assertEqual(
            after["stock"]["Potion"]["quantity"] + self.player.trainer.get_item_quantity("Potion"),
            2 + receipt["delta"]["Potion"],
        )
        self.assertEqual(after["wallet"], before["wallet"] - 300)

    def test_final_copy_competition_after_refill(self):
        """Two buyers cannot duplicate the last newly replenished copy."""
        self.buy("Potion 2")
        self.eligible()
        self.refill()
        self.buy()
        for player in self.players:
            Trainer.objects.filter(pk=player.trainer.pk).update(money=1000)
        before_bags = sum(player.trainer.get_item_quantity("Potion") for player in self.players)
        results = self.race(
            [
                lambda: ShopPurchase(self.players[0]).buy("Potion", 1),
                lambda: ShopPurchase(self.players[1]).buy("Potion", 1),
            ]
        )
        self.assertEqual(sum(result is None for result in results), 1)
        self.assertEqual(
            sum(player.trainer.get_item_quantity("Potion") for player in self.players),
            before_bags + 1,
        )
        self.assertEqual(self.state()["stock"]["Potion"]["quantity"], 0)
        self.assertEqual(
            sum(
                Trainer.objects.filter(pk=player.trainer.pk).values_list("money", flat=True).get()
                for player in self.players
            ),
            1700,
        )

    def test_player_invalid_target_and_full_health_preserve_acquired_copy(self):
        """Refilling stock cannot bypass field target/current-use guards."""
        self.buy()
        self.eligible()
        self.refill()
        self.buy()
        before = self.state()
        self.command("use", "Potion=99")
        self.assertEqual(self.state(), before)
        self.command("use", "Potion=3")
        self.assertEqual(self.state(), before)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        acquisition.load_runtime()
        from evennia.accounts.models import AccountDB
        from evennia.objects.models import ObjectDB
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.trainer import Trainer
        from pokemon.services.item_replenishment import (
            ItemReplenishment,
            ReplenishmentError,
            ReplenishmentPolicy,
        )
        from pokemon.services.item_shop import ShopPurchase, ShopPurchaseError

        try:
            result = unittest.TextTestRunner(verbosity=2).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(ReplenishmentCases)
            )
        finally:
            if os.environ.get("PF2_REPLENISHMENT_EVIDENCE"):
                Path(os.environ["PF2_REPLENISHMENT_EVIDENCE"]).write_text(
                    json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8"
                )
        raise SystemExit(not result.wasSuccessful())

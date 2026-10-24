"""Ordinary marketplace commands, atomic payments, custody and competing buyers."""

import importlib
import json
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres

TRANSCRIPT = []


class MarketCases(unittest.TestCase):
    """Use real ordinary characters, wallets, placements and independent SQL writers."""

    def setUp(self):
        """Create only tagged disposable accounts and assets in the private schema."""
        accounts = [AccountDB.objects.create(username="market-qa-" + uuid4().hex) for _ in range(3)]
        self.seller, self.buyer, self.other, self.alt = [ObjectDB.objects.create(
            db_key="Market QA " + uuid4().hex[:12], db_typeclass_path="pokemon.user.User", db_account=account)
            for account in (*accounts, accounts[0])]
        self.players = (self.seller, self.buyer, self.other, self.alt)
        self.messages, self.steps, self.transports = {}, [], []
        for player in self.players:
            player.permissions.add("Player")
            player.tags.add("october-market-qa")
            Trainer.objects.get_or_create(user=player, defaults={"trainer_number": Trainer.objects.count() + 1})
            UserStorage.objects.get_or_create(user=player)
            Trainer.objects.filter(user=player).update(money=1000)
            self.messages[player.pk] = []
            transport = patch.object(player, "msg", side_effect=self.messages[player.pk].append)
            transport.start()
            self.transports.append(transport)
        self.source = self.mon(self.seller, 3)

    def tearDown(self):
        """Retain normal command evidence and fail on any silently broken custody."""
        for transport in self.transports:
            transport.stop()
        self.assertEqual(list(audit_ownership_v1(apps)), [])
        self.assertEqual(list(audit_market_v1(apps)), [])
        TRANSCRIPT.append({"case": self._testMethodName, "commands": self.steps,
            "transport": "captured; no socket", "permissions": [list(p.permissions.all()) for p in self.players]})

    @staticmethod
    def mon(player, slot, *, boxed=False):
        """Preserve meaningful genetic, held, status and move state across purchases."""
        source = create_owned_pokemon("Squirtle", player.trainer, 20, nature="Hardy", ivs=[1, 2, 3, 4, 5, 6],
                                      evs=[0] * 6, active_move_names=["Tackle", "Water Gun"])
        OwnedPokemon.objects.filter(pk=source.pk).update(held_item="Oran Berry", current_hp=2, status="psn")
        ActiveMoveslot.objects.filter(pokemon=source).update(current_pp=2)
        PlacementService(player.userstorage).to_party(source, slot)
        if boxed:
            PlacementService(player.userstorage).to_box(source)
        return fresh_owned(source.pk)

    @staticmethod
    def money(player):
        """Read the authoritative per-character wallet without object caching."""
        return Trainer.objects.values_list("money", flat=True).get(user_id=player.pk)

    def command(self, player, text):
        """Execute the production command with only outbound messages captured."""
        start = len(self.messages[player.pk])
        command = CmdMarket()
        command.caller, command.args = player, text.removeprefix("+market").strip()
        command.func()
        self.steps.append({"character": player.pk, "input": text, "output": self.messages[player.pk][start:]})
        return self.messages[player.pk][-1]

    def listing(self, *, boxed=False, price=100):
        """Publish using the ordinary party or boxed-ID selector."""
        if boxed:
            PlacementService(self.seller.userstorage).to_box(self.source)
        selector = str(self.source.pk)[:8] if boxed else "3"
        self.command(self.seller, f"+market list {selector}={price}")
        listing = MarketListing.objects.filter(seller_character_id=self.seller.pk).latest("created_at")
        self.command(self.buyer, f"+market inspect {listing.pk}")
        return listing

    def race(self, *actions):
        """Give each competing operation a separate guarded PostgreSQL connection."""
        from django.db import connections

        barrier = Barrier(len(actions))
        def worker(action):
            """Return expected rejection outcomes while surfacing unexpected SQL failures."""
            try:
                barrier.wait(timeout=10)
                return action()
            except PlacementError as error:
                return error
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            return list(pool.map(worker, actions))

    def test_normal_browse_inspect_buy_and_reconnect_preserve_asset_and_money(self):
        before = OwnedPokemon.objects.filter(pk=self.source.pk).values().get()
        listing = self.listing()
        self.assertIn(str(listing.pk), self.command(self.buyer, "+market"))
        self.assertEqual(fresh_owned(self.source.pk).trainer_id, self.seller.trainer.pk)
        self.assertIn("completed", self.command(self.buyer, f"+market buy {listing.pk}"))
        after = OwnedPokemon.objects.filter(pk=self.source.pk).values().get()
        self.assertEqual(after.pop("trainer_id"), self.buyer.trainer.pk)
        before.pop("trainer_id")
        self.assertEqual(after, before)
        self.assertEqual((self.money(self.seller), self.money(self.buyer)), (1100, 900))
        listing.refresh_from_db()
        self.buyer.attributes.reset_cache()
        self.assertIn(listing.receipt["purchase"], self.command(self.buyer, f"+market buy {listing.pk}"))
        self.assertIn("sold", self.command(self.seller, "+market mine"))
        self.assertEqual((self.money(self.seller), self.money(self.buyer)), (1100, 900))

    def test_boxed_source_full_destination_party_and_release_replay(self):
        for slot in range(1, 7):
            self.mon(self.buyer, slot)
        listing = self.listing(boxed=True)
        Marketplace(self.buyer).buy(listing.pk)
        self.assertEqual(PokemonPlacement.objects.get(pokemon_id=self.source.pk).location_type, "box")
        PlacementService(self.buyer.userstorage).release(self.source)
        self.assertFalse(OwnedPokemon.objects.filter(pk=self.source.pk).exists())
        self.assertEqual(Marketplace(self.buyer).buy(listing.pk)["listing"], str(listing.pk))
        self.assertFalse(OwnedPokemon.objects.filter(pk=self.source.pk).exists())

    def test_exact_price_inspection_is_character_bound_and_purchase_claims_are_private(self):
        listing = self.listing()
        self.assertIn("Inspect", self.command(self.other, f"+market buy {listing.pk}"))
        self.assertIn("cannot buy your own", self.command(self.seller, f"+market buy {listing.pk}"))
        self.assertIn("own listings", self.command(self.alt, f"+market cancel {listing.pk}"))
        Marketplace(self.buyer).buy(listing.pk)
        transfer_id = MarketListing.objects.get(pk=listing.pk).receipt["transfer"]["transfer"]
        for actor in (self.seller, self.buyer):
            for operation in ("inspect", "accept", "close"):
                with self.assertRaisesRegex(PlacementError, "market"):
                    getattr(TradeOffers(actor), operation)(transfer_id)
            self.assertFalse(any(str(row.pk) == transfer_id for row in TradeOffers(actor).offers()))

    def test_insufficient_money_invalid_prices_foreign_ids_and_eggs_change_nothing(self):
        for price in ("0", "-1", "1.5", "1000001", "infinity", "9" * 5000):
            self.command(self.seller, f"+market list 3={price}")
        self.command(self.seller, "+market list " + "9" * 5000 + "=100")
        self.command(self.other, f"+market list {self.source.pk}=100")
        self.assertFalse(MarketListing.objects.filter(seller_character_id__in=[p.pk for p in self.players]).exists())
        OwnedPokemon.objects.filter(pk=self.source.pk).update(is_egg=True)
        self.assertIn("hatched", self.command(self.seller, "+market list 3=100"))
        OwnedPokemon.objects.filter(pk=self.source.pk).update(is_egg=False)
        listing = self.listing()
        Trainer.objects.filter(user=self.buyer).update(money=99)
        self.assertIn("enough", self.command(self.buyer, f"+market buy {listing.pk}"))
        self.assertEqual((self.money(self.seller), self.money(self.buyer)), (1000, 99))
        self.assertEqual(fresh_owned(self.source.pk).trainer_id, self.seller.trainer.pk)

    def test_expiry_owner_reclaim_and_cancel_are_durable_idempotent(self):
        listing = self.listing()
        self.command(self.seller, f"+market cancel {listing.pk}")
        self.command(self.seller, f"+market cancel {listing.pk}")
        self.assertIn("no longer", self.command(self.buyer, f"+market buy {listing.pk}"))
        listing = self.listing()
        later = lambda: listing.expires_at + timedelta(seconds=1)
        with self.assertRaisesRegex(PlacementError, "expired"):
            Marketplace(self.buyer, clock=later).buy(listing.pk)
        listing.refresh_from_db()
        self.assertEqual(listing.state, "expired")
        self.assertFalse(PokemonReservation.objects.filter(pokemon=self.source).exists())
        listing = self.listing()
        Marketplace(self.seller, clock=lambda: listing.expires_at + timedelta(seconds=1)).mine()
        self.assertFalse(PokemonReservation.objects.filter(pokemon=self.source).exists())
        self.assertEqual((self.money(self.seller), self.money(self.buyer)), (1000, 1000))

    def test_competing_buyers_pay_and_transfer_exactly_once(self):
        listing = self.listing()
        Marketplace(self.other).inspect(listing.pk)
        results = self.race(lambda: Marketplace(self.buyer).buy(listing.pk), lambda: Marketplace(self.other).buy(listing.pk))
        self.assertEqual(sum(isinstance(value, dict) for value in results), 1)
        self.assertEqual(self.money(self.seller), 1100)
        self.assertEqual(self.money(self.buyer) + self.money(self.other), 1900)
        listing.refresh_from_db()
        self.assertEqual(fresh_owned(self.source.pk).trainer.user_id, listing.buyer_character_id)

    def test_buy_cancel_race_has_one_legal_outcome(self):
        listing = self.listing()
        self.race(lambda: Marketplace(self.buyer).buy(listing.pk), lambda: Marketplace(self.seller).close(listing.pk))
        listing.refresh_from_db()
        sold = listing.state == "sold"
        self.assertIn(listing.state, ("sold", "cancelled"))
        self.assertEqual(fresh_owned(self.source.pk).trainer_id, (self.buyer if sold else self.seller).trainer.pk)
        self.assertEqual(self.money(self.buyer), 900 if sold else 1000)
        self.assertFalse(PokemonReservation.objects.filter(pokemon=self.source).exists())

    def test_failed_debit_or_final_receipt_rolls_back_ownership_claim_and_wallets(self):
        from django.db.models.query import QuerySet

        listing = self.listing()
        original = QuerySet.update
        def fail_wallet(query, **values):
            """Fail after a real wallet write, following the actual ownership transfer."""
            result = original(query, **values)
            if query.model is Trainer and "money" in values:
                raise RuntimeError("wallet fault")
            return result
        for failure in (patch.object(QuerySet, "update", fail_wallet),
                patch.object(MarketListing, "save", side_effect=RuntimeError("receipt fault"))):
            with failure, self.assertRaises(RuntimeError):
                Marketplace(self.buyer).buy(listing.pk)
            listing.refresh_from_db()
            self.assertEqual(listing.state, "active")
            self.assertEqual((self.money(self.seller), self.money(self.buyer)), (1000, 1000))
            self.assertEqual(fresh_owned(self.source.pk).trainer_id, self.seller.trainer.pk)
            self.assertTrue(PokemonReservation.objects.filter(pokemon=self.source, kind="market", token=listing.pk).exists())
        Marketplace(self.buyer).buy(listing.pk)

    def test_changed_asset_or_new_battle_rejects_without_money_loss(self):
        listing = self.listing()
        ActiveMoveslot.objects.filter(pokemon=self.source).update(current_pp=1)
        self.assertIn("changed", self.command(self.buyer, f"+market buy {listing.pk}"))
        Marketplace(self.seller).close(listing.pk)
        listing = self.listing()
        self.buyer.attributes.add("battle_lock", str(uuid4()))
        self.assertIn("battle", self.command(self.buyer, f"+market buy {listing.pk}"))
        self.buyer.attributes.remove("battle_lock")
        self.assertEqual(self.money(self.buyer), 1000)
        with self.assertRaises(PlacementError):
            PlacementService(self.seller.userstorage).release(self.source)

    def test_listing_request_retry_binds_asset_price_and_character(self):
        request_id = uuid4()
        service = Marketplace(self.seller)
        listing = service.create("3", 100, request_id=request_id)
        self.assertEqual(service.create("3", 100, request_id=request_id).pk, listing.pk)
        for selector, price in (("3", 101), (str(self.source.pk), 100)):
            with self.assertRaisesRegex(PlacementError, "different listing"):
                service.create(selector, price, request_id=request_id)
        with self.assertRaises(PlacementError):
            service.create("3", 100)

    def test_database_seals_price_receipt_and_matching_active_claim(self):
        from django.db import IntegrityError, transaction

        listing = self.listing()
        for mutation in (lambda: MarketListing.objects.filter(pk=listing.pk).update(price=101),
                lambda: PokemonReservation.objects.filter(token=listing.pk).delete()):
            with self.assertRaises(IntegrityError), transaction.atomic():
                mutation()
        Marketplace(self.buyer).buy(listing.pk)
        with self.assertRaises(IntegrityError), transaction.atomic():
            MarketListing.objects.filter(pk=listing.pk).update(receipt={})

    def test_purchase_expiry_race_releases_or_sells_with_no_partial_payment(self):
        listing = self.listing()
        now = lambda: listing.expires_at - timedelta(seconds=1)
        expired = lambda: listing.expires_at + timedelta(seconds=1)
        self.race(lambda: Marketplace(self.buyer, clock=now).buy(listing.pk),
                  lambda: Marketplace(self.seller, clock=expired).close(listing.pk, expired_only=True))
        listing.refresh_from_db()
        self.assertIn(listing.state, ("sold", "expired"))
        self.assertEqual(self.money(self.buyer), 900 if listing.state == "sold" else 1000)
        self.assertEqual(self.money(self.seller), 1100 if listing.state == "sold" else 1000)
        self.assertFalse(PokemonReservation.objects.filter(pokemon=self.source).exists())

    def test_destination_failure_and_wallet_limit_leave_listing_and_funds_intact(self):
        listing = self.listing()
        original = PlacementService._party
        def fail_destination(service, *args, **kwargs):
            """Fail after the real destination write, while settlement is still atomic."""
            original(service, *args, **kwargs)
            raise RuntimeError("destination fault")
        with patch.object(PlacementService, "_party", fail_destination), self.assertRaisesRegex(RuntimeError, "destination"):
            Marketplace(self.buyer).buy(listing.pk)
        listing.refresh_from_db()
        self.assertEqual(listing.state, "active")
        self.assertEqual((self.money(self.seller), self.money(self.buyer)), (1000, 1000))
        self.assertEqual(fresh_owned(self.source.pk).trainer_id, self.seller.trainer.pk)
        Trainer.objects.filter(user=self.seller).update(money=Marketplace.maximum_wallet)
        self.assertIn("cannot receive", self.command(self.buyer, f"+market buy {listing.pk}"))
        self.assertEqual(self.money(self.buyer), 1000)

    def test_two_listings_cannot_overdraw_one_competing_buyer_wallet(self):
        first = self.listing(price=800)
        self.source = self.mon(self.seller, 4, boxed=True)
        second = self.listing(boxed=True, price=800)
        results = self.race(lambda: Marketplace(self.buyer).buy(first.pk), lambda: Marketplace(self.buyer).buy(second.pk))
        self.assertEqual(sum(isinstance(value, dict) for value in results), 1)
        self.assertEqual(self.money(self.buyer), 200)
        self.assertEqual(self.money(self.seller), 1800)

    def test_existing_wallet_writers_use_current_money_after_market_purchase(self):
        stale = Trainer.objects.get(user=self.buyer)
        listing = self.listing()
        Marketplace(self.buyer).buy(listing.pk)
        self.assertFalse(stale.spend_money(950))
        stale.add_money(50)
        self.assertEqual(self.money(self.buyer), 950)
        self.assertTrue(stale.spend_money(950))
        self.assertEqual(self.money(self.buyer), 0)
        for amount in (-1, True, "100"):
            with self.assertRaises(ValueError):
                stale.add_money(amount)
            with self.assertRaises(ValueError):
                stale.spend_money(amount)

    def test_existing_credit_racing_a_sale_preserves_both_changes(self):
        stale = Trainer.objects.get(user=self.seller)
        listing = self.listing()
        self.race(lambda: Marketplace(self.buyer).buy(listing.pk), lambda: stale.add_money(7))
        self.assertEqual(self.money(self.seller), 1107)
        self.assertEqual(self.money(self.buyer), 900)

    def test_listing_displays_saved_shiny_state_and_preserves_it_on_purchase(self):
        OwnedPokemon.objects.filter(pk=self.source.pk).update(is_shiny=True)
        listing = self.listing()
        self.assertIs(listing.snapshot["summary"]["shiny"], True)
        self.assertIn("Shiny: yes", self.command(self.buyer, f"+market inspect {listing.pk}"))
        self.command(self.buyer, f"+market buy {listing.pk}")
        self.assertTrue(fresh_owned(self.source.pk).is_shiny)

    def test_older_missing_shiny_listing_cannot_sell_until_seller_publishes_new_terms(self):
        from pokemon.services.trade_snapshot import PokemonTradeSnapshot

        original = PokemonTradeSnapshot.capture
        def old_snapshot(identifier):
            """Preserve the original fingerprint while recreating its missing public value."""
            value = original(identifier)
            value["summary"]["shiny"] = None
            return value
        with patch.object(PokemonTradeSnapshot, "capture", side_effect=old_snapshot):
            listing = self.listing()
        self.assertIn("unrecorded", self.command(self.buyer, f"+market inspect {listing.pk}"))
        self.assertIn("did not record shiny state", self.command(self.buyer, f"+market buy {listing.pk}"))
        self.assertEqual((self.money(self.seller), self.money(self.buyer)), (1000, 1000))
        self.assertEqual(fresh_owned(self.source.pk).trainer_id, self.seller.trainer.pk)
        self.command(self.seller, f"+market cancel {listing.pk}")
        listing = self.listing()
        self.assertIs(listing.snapshot["summary"]["shiny"], False)
        self.assertIn("Shiny: no", self.command(self.buyer, f"+market inspect {listing.pk}"))
        self.assertIn("completed", self.command(self.buyer, f"+market buy {listing.pk}"))


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from evennia.commands.command import Command
        from django.apps import apps
        from django.contrib.contenttypes.models import ContentType
        from django.db import connection
        from evennia.accounts.models import AccountDB
        from evennia.objects.models import ObjectDB
        ContentType.objects.get_for_models(*apps.get_models(), for_concrete_models=False)
        with connection.schema_editor() as editor:
            for name in ("0041_placement_integrity_triggers", "0048_ownership_integrity", "0050_market_integrity"):
                importlib.import_module("pokemon.migrations." + name).install(apps, editor)
        with patch.object(evennia, "Command", Command):
            from commands.player.cmd_market import CmdMarket
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.market import MarketListing
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.models.ownership import PokemonReservation
        from pokemon.models.storage import PokemonPlacement, UserStorage
        from pokemon.models.trainer import Trainer
        from pokemon.services.ownership import fresh_owned
        from pokemon.services.ownership_audit import audit_ownership_v1
        from pokemon.services.market_audit import audit_market_v1
        from pokemon.services.marketplace import Marketplace
        from pokemon.services.placement import PlacementError, PlacementService
        from pokemon.services.trading import TradeOffers
        try:
            unittest.main(verbosity=2)
        finally:
            if os.environ.get("PF2_MARKET_PLAYER_EVIDENCE"):
                Path(os.environ["PF2_MARKET_PLAYER_EVIDENCE"]).write_text(json.dumps(TRANSCRIPT, indent=2, default=str), encoding="utf-8")

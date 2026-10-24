"""Real PostgreSQL Daycare commands, replay, custody constraints and races."""

import importlib
import json
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres

TRANSCRIPT = []


class DaycareCases(unittest.TestCase):
    """Keep original and alternate character authority separate from their accounts."""

    def setUp(self):
        """Create tagged disposable ordinary players with meaningful owned state."""
        accounts = [AccountDB.objects.create(username="daycare-qa-" + uuid4().hex) for _ in range(2)]
        self.player, self.other, self.alt = [ObjectDB.objects.create(db_key="Daycare QA " + uuid4().hex[:12],
            db_typeclass_path="pokemon.user.User", db_account=account) for account in (*accounts, accounts[0])]
        self.players = (self.player, self.other, self.alt)
        self.messages, self.steps, self.transports = {}, [], []
        for player in self.players:
            player.permissions.add("Player")
            player.tags.add("october-daycare-qa")
            Trainer.objects.get_or_create(user=player, defaults={"trainer_number": Trainer.objects.count() + 1})
            UserStorage.objects.get_or_create(user=player)
            Trainer.objects.filter(user=player).update(money=1000)
            self.messages[player.pk] = []
            transport = patch.object(player, "msg", side_effect=self.messages[player.pk].append)
            transport.start()
            self.transports.append(transport)
        self.source = self.mon(3)

    def tearDown(self):
        """Require the current placement/claim audit to accept every final state."""
        for transport in self.transports:
            transport.stop()
        self.assertEqual(list(audit_ownership_v2(apps)), [])
        TRANSCRIPT.append({"case": self._testMethodName, "commands": self.steps,
            "transport": "captured; no socket", "permissions": [list(p.permissions.all()) for p in self.players]})

    def mon(self, slot, *, boxed=False):
        """Retain genetic/held/status/PP values to detect unintended reset or leveling."""
        source = create_owned_pokemon("Squirtle", self.player.trainer, 20, nature="Hardy", ivs=[1, 2, 3, 4, 5, 6],
            evs=[0] * 6, active_move_names=["Tackle", "Water Gun"])
        OwnedPokemon.objects.filter(pk=source.pk).update(held_item="Oran Berry", current_hp=2, status="psn")
        ActiveMoveslot.objects.filter(pokemon=source).update(current_pp=2)
        PlacementService(self.player.userstorage).to_party(source, slot)
        if boxed:
            PlacementService(self.player.userstorage).to_box(source)
        return fresh_owned(source.pk)

    def money(self):
        """Read the saved wallet rather than a cached related Trainer instance."""
        return Trainer.objects.values_list("money", flat=True).get(user_id=self.player.pk)

    def command(self, player, text):
        """Execute the public command with only its outbound transport captured."""
        start = len(self.messages[player.pk])
        command = CmdDaycare()
        command.caller, command.args = player, text.removeprefix("+daycare").strip()
        command.func()
        self.steps.append({"character": player.pk, "input": text, "output": self.messages[player.pk][start:]})
        return self.messages[player.pk][-1]

    def deposit(self, *, boxed=False):
        """Discover the actual saved entry after ordinary deposit."""
        if boxed:
            PlacementService(self.player.userstorage).to_box(self.source)
        selector = str(self.source.pk)[:8] if boxed else "3"
        self.command(self.player, f"+daycare deposit {selector}")
        return DaycareEntry.objects.get(storage=self.player.userstorage, pokemon=self.source, state="active")

    def race(self, *actions):
        """Run each contender on a separate guarded database connection."""
        from django.db import connections

        barrier = Barrier(len(actions))
        def worker(action):
            """Return expected rejections while surfacing SQL/deadlock defects."""
            try:
                barrier.wait(timeout=10)
                return action()
            except PlacementError as error:
                return error
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            return list(pool.map(worker, actions))

    def test_player_deposit_reconnect_retrieve_preserves_exact_saved_pokemon(self):
        before = OwnedPokemon.objects.filter(pk=self.source.pk).values().get()
        moves = list(ActiveMoveslot.objects.filter(pokemon=self.source).order_by("slot").values())
        entry = self.deposit()
        self.assertEqual(self.money(), 900)
        self.assertEqual(PokemonPlacement.objects.get(pokemon=self.source).location_type, "daycare")
        self.assertNotIn(self.source.pk, [mon.pk for mon in self.player.userstorage.get_party()])
        self.player.attributes.reset_cache()
        self.assertIn(str(entry.pk), self.command(self.player, "+daycare"))
        self.command(self.player, f"+daycare deposit {self.source.pk}")
        self.assertEqual(self.money(), 900)
        self.assertIn("retrieval", self.command(self.player, f"+daycare retrieve {entry.pk}"))
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.source.pk).values().get(), before)
        self.assertEqual(list(ActiveMoveslot.objects.filter(pokemon=self.source).order_by("slot").values()), moves)
        self.assertEqual(PokemonPlacement.objects.get(pokemon=self.source).slot, 3)
        self.command(self.player, f"+daycare retrieve {entry.pk}")
        self.assertEqual(self.money(), 900)

    def test_boxed_deposit_full_party_return_and_later_release_receipt(self):
        entry = self.deposit(boxed=True)
        for slot in range(1, 7):
            self.mon(slot)
        receipt = Daycare(self.player).retrieve(entry.pk)
        self.assertEqual(receipt["location"], "box")
        PlacementService(self.player.userstorage).release(self.source)
        self.assertEqual(Daycare(self.player).retrieve(entry.pk), receipt)
        self.assertFalse(OwnedPokemon.objects.filter(pk=self.source.pk).exists())

    def test_foreign_and_same_account_ids_cannot_deposit_or_retrieve(self):
        for player in (self.other, self.alt):
            self.assertIn("your owned", self.command(player, f"+daycare deposit {self.source.pk}"))
        entry = self.deposit()
        for player in (self.other, self.alt):
            self.assertIn("does not belong", self.command(player, f"+daycare retrieve {entry.pk}"))
        self.assertEqual(self.money(), 900)

    def test_ineligible_egg_battle_fusion_and_claims_charge_nothing(self):
        from pokemon.services.ownership import PokemonReservations

        OwnedPokemon.objects.filter(pk=self.source.pk).update(is_egg=True)
        self.assertIn("Eggs", self.command(self.player, "+daycare deposit 3"))
        OwnedPokemon.objects.filter(pk=self.source.pk).update(is_egg=False)
        for key, value in (("battle_lock", str(uuid4())), ("fusion_forms", [str(self.source.pk)])):
            self.player.attributes.add(key, value)
            self.command(self.player, "+daycare deposit 3")
            self.player.attributes.remove(key)
        for kind in ("market", "daycare", "breeding"):
            token = uuid4()
            PokemonReservations(self.player).claim(kind, [self.source.pk], token)
            self.command(self.player, "+daycare deposit 3")
            PokemonReservations(self.player).release(kind, token)
        self.assertEqual(self.money(), 1000)
        self.assertFalse(DaycareEntry.objects.filter(storage=self.player.userstorage).exists())
        Trainer.objects.filter(user=self.player).update(money=99)
        self.assertIn("costs 100", self.command(self.player, "+daycare deposit 3"))
        self.assertEqual(self.money(), 99)

    def test_reserved_source_cannot_escape_to_other_systems(self):
        from pokemon.services.ownership import PokemonReservations

        self.deposit()
        for operation in (lambda: PlacementService(self.player.userstorage).release(self.source),
                lambda: PlacementService(self.player.userstorage).to_party(self.source),
                lambda: TradeOffers(self.player).propose(self.other.key, str(self.source.pk)),
                lambda: Marketplace(self.player).create(str(self.source.pk), 100),
                lambda: PokemonReservations(self.player).claim("breeding", [self.source.pk], uuid4())):
            with self.assertRaises(PlacementError):
                operation()
        from pokemon.helpers.party_helpers import has_usable_pokemon
        from utils.fusion import get_battle_party_with_fusion

        self.assertNotIn(self.source.pk, [mon.pk for mon in get_battle_party_with_fusion(self.player)])
        self.assertFalse(has_usable_pokemon(self.player))
        self.assertEqual(PokemonPlacement.objects.get(pokemon=self.source).location_type, "daycare")
        self.assertEqual(PokemonReservation.objects.get(pokemon=self.source).kind, "daycare")

    def test_concurrent_same_deposit_and_retrieval_charge_once(self):
        results = self.race(lambda: Daycare(self.player).deposit(str(self.source.pk)),
                            lambda: Daycare(self.player).deposit(str(self.source.pk)))
        self.assertEqual(results[0].pk, results[1].pk)
        self.assertEqual(self.money(), 900)
        entry = results[0]
        returned = self.race(lambda: Daycare(self.player).retrieve(entry.pk), lambda: Daycare(self.player).retrieve(entry.pk))
        self.assertEqual(returned[0], returned[1])
        self.assertFalse(PokemonReservation.objects.filter(pokemon=self.source).exists())

    def test_competing_deposits_enforce_two_place_capacity_without_third_fee(self):
        sources = (self.source, self.mon(1), self.mon(2))
        results = self.race(*(lambda source=source: Daycare(self.player).deposit(str(source.pk)) for source in sources))
        self.assertEqual(sum(isinstance(row, DaycareEntry) for row in results), 2)
        self.assertEqual(self.money(), 800)
        self.assertEqual(DaycareEntry.objects.filter(storage=self.player.userstorage, state="active").count(), 2)

    def test_fee_and_retrieval_receipt_faults_restore_complete_prior_state(self):
        from django.db.models.query import QuerySet

        original = QuerySet.update
        def fail_fee(query, **values):
            """Inject failure after the actual wallet and custody writes."""
            result = original(query, **values)
            if query.model is Trainer and "money" in values:
                raise RuntimeError("fee fault")
            return result
        with patch.object(QuerySet, "update", fail_fee), self.assertRaisesRegex(RuntimeError, "fee"):
            Daycare(self.player).deposit("3")
        self.assertEqual(self.money(), 1000)
        self.assertEqual(PokemonPlacement.objects.get(pokemon=self.source).location_type, "party")
        self.assertFalse(PokemonReservation.objects.filter(pokemon=self.source).exists())
        entry = self.deposit()
        with patch.object(DaycareEntry, "save", side_effect=RuntimeError("receipt fault")), self.assertRaises(RuntimeError):
            Daycare(self.player).retrieve(entry.pk)
        entry.refresh_from_db()
        self.assertEqual(entry.state, "active")
        self.assertEqual(PokemonPlacement.objects.get(pokemon=self.source).location_type, "daycare")
        self.assertTrue(PokemonReservation.objects.filter(token=entry.pk).exists())
        Daycare(self.player).retrieve(entry.pk)

    def test_database_rejects_orphan_custody_and_deleted_active_claim(self):
        from django.db import IntegrityError, transaction

        with self.assertRaises(IntegrityError), transaction.atomic():
            PlacementService(self.player.userstorage)._write(self.source, self.player.userstorage,
                PokemonPlacement.objects.get(pokemon=self.source), "daycare")
        entry = self.deposit()
        with self.assertRaises(IntegrityError), transaction.atomic():
            PokemonReservation.objects.filter(token=entry.pk).delete()

    def test_retrieval_racing_trade_or_market_has_one_valid_custody_state(self):
        for destination in ("trade", "market"):
            entry = self.deposit()
            action = (lambda: TradeOffers(self.player).propose(self.other.key, str(self.source.pk))) if destination == "trade" else (
                lambda: Marketplace(self.player).create(str(self.source.pk), 100))
            results = self.race(lambda: Daycare(self.player).retrieve(entry.pk), action)
            entry.refresh_from_db()
            self.assertEqual(entry.state, "retrieved")
            self.assertEqual(fresh_owned(self.source.pk).trainer_id, self.player.trainer.pk)
            if not isinstance(results[1], PlacementError):
                if destination == "trade":
                    TradeOffers(self.player).close(results[1].pk)
                else:
                    Marketplace(self.player).close(results[1].pk)
            self.assertFalse(PokemonReservation.objects.filter(pokemon=self.source).exists())
            self.assertEqual(list(audit_ownership_v2(apps)), [])

    def test_operator_inspection_is_read_only_and_retrieval_is_the_recovery_route(self):
        import io
        from django.core.management import call_command

        entry = self.deposit()
        before = (self.money(), list(DaycareEntry.objects.filter(pk=entry.pk).values()),
                  list(PokemonPlacement.objects.filter(pokemon=self.source).values()))
        output = io.StringIO()
        call_command("audit_pokemon_daycare", entry=str(entry.pk), stdout=output)
        self.assertIn(str(entry.pk), output.getvalue())
        self.assertIn("No data was changed", output.getvalue())
        self.assertEqual(before, (self.money(), list(DaycareEntry.objects.filter(pk=entry.pk).values()),
            list(PokemonPlacement.objects.filter(pokemon=self.source).values())))


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
            for name in ("0041_placement_integrity_triggers", "0048_ownership_integrity", "0050_market_integrity", "0052_daycare_integrity"):
                importlib.import_module("pokemon.migrations." + name).install(apps, editor)
        with patch.object(evennia, "Command", Command):
            from commands.player.cmd_daycare import CmdDaycare
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.daycare import DaycareEntry
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.models.ownership import PokemonReservation
        from pokemon.models.storage import PokemonPlacement, UserStorage
        from pokemon.models.trainer import Trainer
        from pokemon.services.daycare import Daycare
        from pokemon.services.ownership import fresh_owned, claim_battle
        from pokemon.services.ownership_audit import audit_ownership_v2
        from pokemon.services.marketplace import Marketplace
        from pokemon.services.placement import PlacementError, PlacementService
        from pokemon.services.trading import TradeOffers
        try:
            unittest.main(verbosity=2)
        finally:
            if os.environ.get("PF2_DAYCARE_PLAYER_EVIDENCE"):
                Path(os.environ["PF2_DAYCARE_PLAYER_EVIDENCE"]).write_text(json.dumps(TRANSCRIPT, indent=2, default=str), encoding="utf-8")

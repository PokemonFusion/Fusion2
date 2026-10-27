"""Ordinary consent-trading commands, ownership guards and races in private SQL."""

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


class TradeCases(unittest.TestCase):
    """Use actual accounts, User typeclasses, canonical assets and normal commands."""

    def setUp(self):
        """Separate account ownership from the active character's authority."""
        accounts = [AccountDB.objects.create(username="trade-qa-" + uuid4().hex) for _ in range(2)]
        self.a, self.b, self.alt = [ObjectDB.objects.create(db_key="Trade QA " + uuid4().hex[:12],
            db_typeclass_path="pokemon.user.User", db_account=account) for account in (accounts[0], accounts[1], accounts[0])]
        self.left = self.mon(self.a, "Squirtle", 3)
        self.right = self.mon(self.b, "Pikachu", 6, boxed=True)
        self.messages = {player.pk: [] for player in (self.a, self.b, self.alt)}
        self.steps = []
        self.transports = []
        for player in (self.a, self.b, self.alt):
            player.permissions.add("Player")
            transport = patch.object(player, "msg", side_effect=self.messages[player.pk].append)
            transport.start()
            self.transports.append(transport)

    def tearDown(self):
        """Preserve evidence and reject any silent custody/mirror damage."""
        for transport in self.transports:
            transport.stop()
        self.assertEqual(list(audit_ownership_v1(apps)), [])
        TRANSCRIPT.append({"case": self._testMethodName, "commands": self.steps,
                           "transport": "captured; no socket", "permissions": [list(p.permissions.all()) for p in (self.a, self.b)]})

    @staticmethod
    def mon(player, species, slot, *, boxed=False):
        """Keep gapped canonical positions and meaningful held/HP/PP state."""
        trainer, _ = Trainer.objects.get_or_create(user=player, defaults={"trainer_number": Trainer.objects.count() + 1})
        storage, _ = UserStorage.objects.get_or_create(user=player)
        pokemon = create_owned_pokemon(species, trainer, 20, nature="Hardy", ivs=[1, 2, 3, 4, 5, 6],
                                       evs=[0] * 6, active_move_names=["Tackle", "Water Gun"])
        OwnedPokemon.objects.filter(pk=pokemon.pk).update(held_item="Oran Berry", current_hp=2, status="psn")
        ActiveMoveslot.objects.filter(pokemon=pokemon).update(current_pp=2)
        PlacementService(storage).to_party(pokemon, slot)
        if boxed:
            PlacementService(storage).to_box(pokemon)
        return fresh_owned(pokemon.pk)

    def command(self, player, text):
        """Invoke the actual public command with only its outbound transport captured."""
        start = len(self.messages[player.pk])
        command = CmdTradePokemon()
        command.caller, command.args = player, text.removeprefix("+trade").strip()
        command.func()
        self.steps.append({"character": player.pk, "input": text, "output": self.messages[player.pk][start:]})
        return self.messages[player.pk][-1]

    def offer(self):
        """Discover the newly persisted offer through the player's own list."""
        self.command(self.a, f"+trade offer {self.b.key}=3")
        operation = TradeOffers(self.a).offers()[0]
        self.command(self.b, f"+trade inspect {operation.pk}")
        return operation

    def test_gift_requires_recipient_acceptance_and_receipt_survives_reconnect(self):
        before = OwnedPokemon.objects.filter(pk=self.left.pk).values().get()
        operation = self.offer()
        self.assertEqual(fresh_owned(self.left.pk).trainer_id, self.a.trainer.pk)
        self.command(self.b, "+trade")
        self.assertIn(str(operation.pk), self.messages[self.b.pk][-1])
        self.command(self.b, f"+trade inspect {operation.pk}")
        self.assertIn("Squirtle", self.messages[self.b.pk][-1])
        self.command(self.b, f"+trade accept {operation.pk}")
        after = OwnedPokemon.objects.filter(pk=self.left.pk).values().get()
        self.assertEqual(after.pop("trainer_id"), self.b.trainer.pk)
        before.pop("trainer_id")
        self.assertEqual(after, before)
        self.b.attributes.reset_cache()
        self.command(self.b, "+trade")
        self.assertIn("completed", self.messages[self.b.pk][-1])
        self.command(self.b, f"+trade accept {operation.pk}")
        self.assertEqual(OwnershipTransfer.objects.filter(pk=operation.pk, state="completed").count(), 1)

    def test_counteroffer_invalidates_old_consent_then_swaps_party_and_box(self):
        old = self.offer()
        self.command(self.b, f"+trade counter {old.pk}={str(self.right.pk)[:8]}")
        replacement = TradeOffers(self.b).offers()[0]
        self.assertNotEqual(old.pk, replacement.pk)
        self.assertEqual(replacement.approvals, [self.b.pk])
        self.command(self.b, f"+trade accept {old.pk}")
        self.assertNotEqual(fresh_owned(self.left.pk).trainer_id, self.b.trainer.pk)
        self.command(self.a, f"+trade inspect {replacement.pk}")
        self.command(self.a, f"+trade accept {replacement.pk}")
        self.assertEqual(fresh_owned(self.left.pk).trainer_id, self.b.trainer.pk)
        self.assertEqual(fresh_owned(self.right.pk).trainer_id, self.a.trainer.pk)
        old.refresh_from_db()
        self.assertEqual(old.result["reason"], "countered")
        self.assertEqual(old.result["replacement"], str(replacement.pk))

    def test_decline_cancel_and_expiry_never_move_or_keep_assets_unrecoverable(self):
        for action, actor in (("decline", self.b), ("cancel", self.a)):
            operation = self.offer()
            self.command(actor, f"+trade {action} {operation.pk}")
            self.command(self.b, f"+trade accept {operation.pk}")
            self.assertEqual(fresh_owned(self.left.pk).trainer_id, self.a.trainer.pk)
            self.assertFalse(PokemonReservation.objects.filter(pokemon=self.left).exists())
        operation = self.offer()
        later = lambda: operation.expires_at + timedelta(seconds=1)
        with self.assertRaises(PlacementError):
            TradeOffers(self.b, clock=later).accept(operation.pk)
        self.assertEqual(TradeOffers(self.a, clock=later).close(operation.pk).state, "expired")
        self.assertFalse(PokemonReservation.objects.filter(pokemon=self.left).exists())

    def test_foreign_ids_and_same_account_alt_cannot_act_on_an_offer(self):
        operation = self.offer()
        for action in ("inspect", "accept", "decline", "cancel"):
            self.command(self.alt, f"+trade {action} {operation.pk}")
            self.assertIn("does not belong", self.messages[self.alt.pk][-1])
        self.command(self.b, f"+trade counter {operation.pk}={self.left.pk}")
        self.assertIn("your owned", self.messages[self.b.pk][-1])
        operation.refresh_from_db()
        self.assertEqual(operation.state, "pending")
        from types import SimpleNamespace
        from pokemon.services.ownership import OwnershipTransfers

        for wrong_actor in (self.a.account, SimpleNamespace(pk=self.a.pk)):
            with self.assertRaisesRegex(PlacementError, "active character"):
                OwnershipTransfers(wrong_actor)

    def test_changed_pp_or_held_terms_cannot_be_accepted(self):
        operation = self.offer()
        ActiveMoveslot.objects.filter(pokemon=self.left).update(current_pp=1)
        self.command(self.b, f"+trade accept {operation.pk}")
        self.assertIn("changed", self.messages[self.b.pk][-1])
        self.assertEqual(fresh_owned(self.left.pk).trainer_id, self.a.trainer.pk)
        TradeOffers(self.a).close(operation.pk)
        operation = self.offer()
        OwnedPokemon.objects.filter(pk=self.left.pk).update(held_item="Sitrus Berry")
        self.command(self.b, f"+trade accept {operation.pk}")
        self.assertIn("changed", self.messages[self.b.pk][-1])

    def race(self, *actions):
        """Run independent PostgreSQL connections with a synchronized start."""
        from django.db import connections

        barrier = Barrier(len(actions))
        def worker(action):
            try:
                barrier.wait(timeout=10)
                return action()
            except PlacementError as error:
                return error
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            return list(pool.map(worker, actions))

    def test_competing_accepts_commit_once_and_cancel_race_is_legal(self):
        operation = self.offer()
        results = self.race(lambda: TradeOffers(self.b).accept(operation.pk), lambda: TradeOffers(self.b).accept(operation.pk))
        self.assertEqual(results[0], results[1])
        self.assertEqual(fresh_owned(self.left.pk).trainer_id, self.b.trainer.pk)
        self.left = self.mon(self.a, "Squirtle", 3)
        operation = self.offer()
        self.race(lambda: TradeOffers(self.b).accept(operation.pk), lambda: TradeOffers(self.a).close(operation.pk))
        operation.refresh_from_db()
        self.assertIn(operation.state, ("completed", "cancelled"))

    def test_swap_failure_rolls_back_both_owners_and_consent(self):
        operation = self.offer()
        self.command(self.b, f"+trade counter {operation.pk}={self.right.pk}")
        replacement = TradeOffers(self.b).offers()[0]
        self.command(self.a, f"+trade inspect {replacement.pk}")
        original = PlacementService._party
        calls = []
        def fail_second(service, *args, **kwargs):
            """Exercise failure after the first actual destination write."""
            result = original(service, *args, **kwargs)
            calls.append(1)
            if len(calls) == 2:
                raise RuntimeError("injected destination failure")
            return result
        with patch.object(PlacementService, "_party", fail_second), self.assertRaises(RuntimeError):
            TradeOffers(self.a).accept(replacement.pk)
        self.assertEqual(fresh_owned(self.left.pk).trainer_id, self.a.trainer.pk)
        self.assertEqual(fresh_owned(self.right.pk).trainer_id, self.b.trainer.pk)
        replacement.refresh_from_db()
        self.assertEqual(replacement.approvals, [self.b.pk])
        TradeOffers(self.a).accept(replacement.pk)

    def center(self):
        """Provide a tagged local Center without changing any world/game objects."""
        room = ObjectDB.objects.create(db_key="Trade move Center " + uuid4().hex,
                                       db_typeclass_path="typeclasses.rooms.Room")
        room.db.is_pokemon_center = True
        self.a.location = room
        return room

    def test_move_learning_and_open_moveset_replies_cannot_edit_reserved_or_sold_asset(self):
        """Every retained menu source is checked before reading/writing its moves."""
        from menus import learn_move as learn_menu, moveset_manager
        from pokemon.utils.move_learning import learn_move

        self.center()
        self.a.ndb.ms_pokemon, self.a.ndb.ms_index = self.left, 0
        before = list(ActiveMoveslot.objects.filter(pokemon=self.left).order_by("slot").values())
        learned = set(self.left.learned_moves.values_list("pk", flat=True))
        operation = self.offer()
        learn_move(self.left, "Withdraw", caller=self.a)
        result = learn_menu.node_replace(self.a, pokemon=self.left, move_name="Withdraw", slot=0)
        self.assertIn("reserved", result[0])
        result = moveset_manager.node_edit(self.a, "Tackle")
        self.assertIn("reserved", result[0])
        self.assertEqual(list(ActiveMoveslot.objects.filter(pokemon=self.left).order_by("slot").values()), before)
        self.assertEqual(set(self.left.learned_moves.values_list("pk", flat=True)), learned)
        TradeOffers(self.b).accept(operation.pk)
        result = learn_menu.node_replace(self.a, pokemon=self.left, move_name="Withdraw", slot=0)
        self.assertIn("does not belong", result[0])
        result = moveset_manager.node_edit(self.a, "Tackle")
        self.assertIn("does not belong", result[0])
        self.assertEqual(list(ActiveMoveslot.objects.filter(pokemon=self.left).order_by("slot").values()), before)

    def test_moves_use_has_a_real_guarded_center_route_and_no_field_pp_refill(self):
        """Repair the missing swap method without introducing free field restoration."""
        import evennia
        from evennia.commands.command import Command

        with patch.object(evennia, "Command", Command):
            from commands.player.cmd_learn_evolve import CmdChooseMoveset
        def use():
            """Use the shipped command, not a replacement moveset mutation."""
            command = CmdChooseMoveset()
            command.caller, command.args = self.a, "3=1"
            command.parse()
            command.func()
        self.a.location = None
        use()
        self.assertIn("Pokemon Center", self.messages[self.a.pk][-1])
        self.assertEqual(set(ActiveMoveslot.objects.filter(pokemon=self.left).values_list("current_pp", flat=True)), {2})
        self.center()
        use()
        self.assertIn("now using moveset 1", self.messages[self.a.pk][-1])
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.left.pk).values_list("current_hp", flat=True).get(), 2)
        operation = self.offer()
        before = list(ActiveMoveslot.objects.filter(pokemon=self.left).order_by("slot").values())
        use()
        self.assertIn("reserved", self.messages[self.a.pk][-1])
        self.assertEqual(list(ActiveMoveslot.objects.filter(pokemon=self.left).order_by("slot").values()), before)
        TradeOffers(self.a).close(operation.pk)

    def test_final_commit_rechecks_battle_fusion_and_each_system_claim(self):
        """Preparing a trade never bypasses a system's current eligibility."""
        from pokemon.services.ownership import PokemonReservations

        for kind in ("market", "daycare", "breeding"):
            token = uuid4()
            PokemonReservations(self.a).claim(kind, [self.left.pk], token)
            self.command(self.a, f"+trade offer {self.b.key}=3")
            self.assertIn("reserved", self.messages[self.a.pk][-1])
            PokemonReservations(self.a).release(kind, token)
        self.a.db.fusion_forms = [str(self.left.pk)]
        self.command(self.a, f"+trade offer {self.b.key}=3")
        self.assertIn("Fusion", self.messages[self.a.pk][-1])
        self.a.attributes.remove("fusion_forms")
        operation = self.offer()
        self.b.db.battle_lock = "fresh battle after offer"
        self.command(self.b, f"+trade accept {operation.pk}")
        self.assertIn("battle", self.messages[self.b.pk][-1])
        self.b.attributes.remove("battle_lock")
        self.command(self.b, f"+trade accept {operation.pk}")
        self.assertEqual(fresh_owned(self.left.pk).trainer_id, self.b.trainer.pk)

    def test_full_party_uses_box_and_a_missing_canonical_slot_cannot_offer(self):
        """Automatic overflow is explicit and gapped slots never compact."""
        self.command(self.a, f"+trade offer {self.b.key}=1")
        self.assertIn("no Pokemon", self.messages[self.a.pk][-1])
        for slot in range(1, 7):
            self.mon(self.b, "Squirtle", slot)
        operation = self.offer()
        self.command(self.b, f"+trade accept {operation.pk}")
        self.assertEqual(PokemonPlacement.objects.get(pokemon=self.left).location_type, "box")

    def test_failed_counter_preserves_the_old_offer_and_its_reservation(self):
        """A rejected replacement cannot strand the original proposer's asset."""
        from pokemon.services.ownership import PokemonReservations

        old = self.offer()
        token = uuid4()
        PokemonReservations(self.b).claim("market", [self.right.pk], token)
        self.command(self.b, f"+trade counter {old.pk}={self.right.pk}")
        old.refresh_from_db()
        self.assertEqual(old.state, "pending")
        self.assertEqual(PokemonReservation.objects.get(pokemon=self.left).token, old.pk)
        self.assertEqual(len(TradeOffers(self.b).offers()), 1)

    def test_acceptance_vs_a_pending_move_edit_cannot_mutate_the_new_owner(self):
        """The counterparty's unreserved asset either changes first or transfers first."""
        from pokemon.utils.move_learning import learn_move

        old = self.offer()
        self.command(self.b, f"+trade counter {old.pk}={self.right.pk}")
        replacement = TradeOffers(self.b).offers()[0]
        self.command(self.a, f"+trade inspect {replacement.pk}")
        before = list(ActiveMoveslot.objects.filter(pokemon=self.left).order_by("slot").values())
        self.race(lambda: TradeOffers(self.a).accept(replacement.pk),
                  lambda: learn_move(self.left, "Withdraw", caller=self.a))
        replacement.refresh_from_db()
        self.assertIn(replacement.state, ("pending", "completed"))
        if replacement.state == "completed":
            self.assertEqual(fresh_owned(self.left.pk).trainer_id, self.b.trainer.pk)
            self.assertEqual(list(ActiveMoveslot.objects.filter(pokemon=self.left).order_by("slot").values()), before)
        else:
            self.assertEqual(fresh_owned(self.left.pk).trainer_id, self.a.trainer.pk)
            self.assertNotEqual(list(ActiveMoveslot.objects.filter(pokemon=self.left).order_by("slot").values()), before)

    def test_completed_acceptance_after_release_returns_receipt_without_resurrection(self):
        """A durable offer result remains historical after later legitimate release."""
        operation = self.offer()
        receipt = TradeOffers(self.b).accept(operation.pk)
        identifier = self.left.pk
        PlacementService(self.b.storage).release(fresh_owned(identifier))
        self.assertEqual(TradeOffers(self.b).accept(operation.pk), receipt)
        self.assertFalse(OwnedPokemon.objects.filter(pk=identifier).exists())

    def test_accept_and_counter_require_this_characters_review_of_exact_current_terms(self):
        """Displayed-terms consent cannot carry from a previous offer or an alt."""
        self.command(self.a, f"+trade offer {self.b.key}=3")
        old = TradeOffers(self.a).offers()[0]
        self.command(self.b, f"+trade accept {old.pk}")
        self.assertIn("Inspect these exact terms first", self.messages[self.b.pk][-1])
        self.command(self.b, f"+trade counter {old.pk}={self.right.pk}")
        self.assertIn("Inspect these exact terms first", self.messages[self.b.pk][-1])
        self.command(self.b, f"+trade inspect {old.pk}")
        self.command(self.b, f"+trade counter {old.pk}={self.right.pk}")
        replacement = TradeOffers(self.b).offers()[0]
        self.command(self.a, f"+trade accept {replacement.pk}")
        self.assertIn("Inspect these exact terms first", self.messages[self.a.pk][-1])
        self.command(self.a, f"+trade inspect {replacement.pk}")
        self.command(self.a, f"+trade accept {replacement.pk}")
        self.assertEqual(fresh_owned(self.left.pk).trainer_id, self.b.trainer.pk)

    def test_actual_player_learning_still_commits_and_outer_failure_publishes_nothing(self):
        """An ownership guard must retain ordinary learning and its commit boundary."""
        from django.db import transaction
        from pokemon.utils.move_learning import learn_move

        before = list(ActiveMoveslot.objects.filter(pokemon=self.left).order_by("slot").values())
        start = len(self.messages[self.a.pk])
        with self.assertRaisesRegex(RuntimeError, "outer"), transaction.atomic():
            learn_move(self.left, "Withdraw", caller=self.a)
            raise RuntimeError("outer learning failure")
        self.assertEqual(list(ActiveMoveslot.objects.filter(pokemon=self.left).order_by("slot").values()), before)
        self.assertEqual(len(self.messages[self.a.pk]), start)
        learn_move(self.left, "Withdraw", caller=self.a)
        self.assertTrue(ActiveMoveslot.objects.filter(pokemon=self.left, move__name__iexact="Withdraw").exists())
        self.assertIn("learned Withdraw", self.messages[self.a.pk][-1])

    def test_move_write_failure_rolls_back_without_a_false_success_notice(self):
        """Exercise the existing utility through a real player and actual child writes."""
        from pokemon.utils import move_learning

        before = list(ActiveMoveslot.objects.filter(pokemon=self.left).order_by("slot").values())
        start = len(self.messages[self.a.pk])
        with patch.object(move_learning, "apply_active_moveset", side_effect=RuntimeError("injected move write")):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                move_learning.learn_move(self.left, "Withdraw", caller=self.a)
        self.assertEqual(list(ActiveMoveslot.objects.filter(pokemon=self.left).order_by("slot").values()), before)
        self.assertEqual(len(self.messages[self.a.pk]), start)

    def test_saved_shiny_boolean_is_displayed_and_preserved_through_player_trade(self):
        from pokemon.services.trade_snapshot import PokemonTradeSnapshot

        self.assertIs(PokemonTradeSnapshot.capture(self.left.pk)["summary"]["shiny"], False)
        OwnedPokemon.objects.filter(pk=self.left.pk).update(is_shiny=True)
        operation = self.offer()
        self.assertIs(operation.terms[0]["snapshot"]["summary"]["shiny"], True)
        self.assertIn("shiny; Tera", self.command(self.b, f"+trade inspect {operation.pk}"))
        self.assertNotIn("not shiny; Tera", self.messages[self.b.pk][-1])
        self.command(self.b, f"+trade accept {operation.pk}")
        self.assertTrue(fresh_owned(self.left.pk).is_shiny)

    def test_old_missing_shiny_summary_requires_new_terms_before_accept_or_counter(self):
        from pokemon.services.trade_snapshot import PokemonTradeSnapshot

        original = PokemonTradeSnapshot.capture
        def old_snapshot(identifier):
            """Reproduce only the earlier recorded summary shape before sealing terms."""
            value = original(identifier)
            value["summary"]["shiny"] = None
            return value
        with patch.object(PokemonTradeSnapshot, "capture", side_effect=old_snapshot):
            operation = self.offer()
        self.assertIn("unrecorded shiny state", self.command(self.b, f"+trade inspect {operation.pk}"))
        for command in (f"+trade accept {operation.pk}", f"+trade counter {operation.pk}={self.right.pk}"):
            self.assertIn("did not record shiny state", self.command(self.b, command))
        operation.refresh_from_db()
        self.assertEqual(operation.state, "pending")
        self.assertEqual(fresh_owned(self.left.pk).trainer_id, self.a.trainer.pk)
        self.command(self.a, f"+trade cancel {operation.pk}")
        self.assertFalse(PokemonReservation.objects.filter(pokemon=self.left).exists())


    def test_paid_mint_is_visible_and_preserved_by_ordinary_trade(self):
        """A separately labelled bag prerequisite funds training before genuine consent."""
        from pokemon.services.field_mints import FieldMintUse
        from pokemon.helpers.pokemon_helpers import get_stats

        self.a.trainer.add_item("Adamant Mint")
        self.assertTrue(FieldMintUse(self.a).use("Adamant Mint", "3"))
        expected = get_stats(fresh_owned(self.left.pk))
        operation = self.offer()
        text = self.command(self.b, f"+trade inspect {operation.pk}")
        self.assertIn("Adamant", text)
        self.assertIn("Hardy", text)
        self.command(self.b, f"+trade accept {operation.pk}")
        current = fresh_owned(self.left.pk)
        self.assertEqual(current.trainer_id, self.b.trainer.pk)
        self.assertEqual((current.nature, current.trained_stat_nature), ("Hardy", "Adamant"))
        self.assertEqual(get_stats(current), expected)

    def test_changed_mint_training_invalidates_exact_trade_review(self):
        """A labelled out-of-band saved change cannot inherit another asset's consent."""
        operation = self.offer()
        OwnedPokemon.objects.filter(pk=self.left.pk).update(trained_stat_nature="Adamant")
        self.command(self.b, f"+trade accept {operation.pk}")
        self.assertIn("changed", self.messages[self.b.pk][-1])
        self.assertEqual(fresh_owned(self.left.pk).trainer_id, self.a.trainer.pk)
        self.command(self.a, f"+trade cancel {operation.pk}")


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
            importlib.import_module("pokemon.migrations.0041_placement_integrity_triggers").install(apps, editor)
            importlib.import_module("pokemon.migrations.0048_ownership_integrity").install(apps, editor)
        with patch.object(evennia, "Command", Command):
            from commands.player.cmd_account import CmdTradePokemon
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.models.ownership import OwnershipTransfer, PokemonReservation
        from pokemon.models.storage import PokemonPlacement, UserStorage
        from pokemon.models.trainer import Trainer
        from pokemon.services.ownership import fresh_owned
        from pokemon.services.ownership_audit import audit_ownership_v1
        from pokemon.services.placement import PlacementError, PlacementService
        from pokemon.services.trading import TradeOffers
        try:
            unittest.main(verbosity=2)
        finally:
            if os.environ.get("PF2_TRADE_PLAYER_EVIDENCE"):
                Path(os.environ["PF2_TRADE_PLAYER_EVIDENCE"]).write_text(json.dumps(TRANSCRIPT, indent=2, default=str), encoding="utf-8")

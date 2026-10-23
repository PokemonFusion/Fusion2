"""Real PostgreSQL transfer, reservation, receipt and competing-writer checks.

Run with an explicit PF2_TEST_POSTGRES_DSN. Tables and constraint functions are
built only in a generated schema; no deployment migrations or game data are used.
"""

import importlib
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from isolated_postgres import IsolatedPostgres

database = IsolatedPostgres()
database.__enter__()

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, connection, connections, transaction
from django.utils import timezone
from evennia.objects.models import ObjectDB

from pokemon.models.core import OwnedPokemon
from pokemon.models.ownership import OwnershipTransfer, PokemonReservation
from pokemon.models.storage import PokemonPlacement, StorageBox, UserStorage
from pokemon.models.trainer import Trainer
from pokemon.services.ownership import OwnershipError, OwnershipTransfers, PokemonReservations, fresh_owned
from pokemon.services.ownership_audit import audit_ownership_v1
from pokemon.services.placement import PlacementError, PlacementService


class OwnershipCases(unittest.TestCase):
    """Use persisted character identities, canonical placements and independent SQL."""

    def setUp(self):
        """Give each scenario independent ordinary character custody."""
        self.a, self.b, self.c = [self.character() for _ in range(3)]
        self.left, self.right = self.mon(self.a), self.mon(self.b, party=False)
        self.service = OwnershipTransfers(self.a)

    @staticmethod
    def character():
        """Create a disposable character with explicit trainer and storage."""
        user = ObjectDB.objects.create(db_key="October QA " + uuid4().hex,
                                       db_typeclass_path="pokemon.user.User")
        Trainer.objects.get_or_create(user=user, defaults={"trainer_number": Trainer.objects.count() + 1})
        UserStorage.objects.get_or_create(user=user)
        return user

    @staticmethod
    def mon(owner, *, party=True):
        """Create a fully placed asset without bypassing the creation transaction."""
        with transaction.atomic():
            mon = OwnedPokemon.objects.create(trainer=owner.trainer, species="Pikachu",
                                               ivs=[1, 2, 3, 4, 5, 6], evs=[0] * 6,
                                               nickname="Retain me", held_item="Oran Berry",
                                               current_hp=2, status="psn", total_exp=200,
                                               original_trainer=owner.trainer,
                                               original_trainer_name=owner.key,
                                               obtained_method="test fixture")
            service = PlacementService(UserStorage.objects.get(user=owner))
            service.to_party(mon) if party else service.to_box(mon)
        return mon

    def offer(self, *, swap=False, mode="auto", slot=None):
        """Bind stable IDs and explicit destination policy to immutable terms."""
        moves = [{"pokemon": self.left.pk, "source": self.a.pk, "destination": self.b.pk,
                  "mode": mode, "slot": slot}]
        if swap:
            moves.append({"pokemon": self.right.pk, "source": self.b.pk, "destination": self.a.pk})
        return self.service.prepare(self.b.pk, moves)

    def tearDown(self):
        """Every scenario, including rejected requests, must leave legal custody."""
        self.assertEqual(list(audit_ownership_v1(apps)), [])

    def test_party_and_box_swap_preserves_identity_provenance_and_state(self):
        from pokemon.models.moves import ActiveMoveslot, Move, MovePPBoost, PokemonLearnedMove

        move, _ = Move.objects.get_or_create(name="Thunder Shock")
        slot = ActiveMoveslot.objects.create(pokemon=self.left, move=move, slot=3, current_pp=2)
        boost = MovePPBoost.objects.create(pokemon=self.left, move=move, bonus_pp=6)
        learned = PokemonLearnedMove.objects.create(pokemon=self.left, move=move)
        before = dict(OwnedPokemon.objects.filter(pk=self.left.pk).values().get())
        operation = self.offer(swap=True)
        self.assertEqual(fresh_owned(self.left.pk).trainer_id, self.a.trainer.pk)
        self.assertFalse(PokemonReservation.objects.filter(pokemon=self.right).exists())
        with self.assertRaisesRegex(OwnershipError, "Both characters"):
            self.service.commit(operation.pk)
        OwnershipTransfers(self.b).approve(operation.pk)
        receipt = self.service.commit(operation.pk)
        after = dict(OwnedPokemon.objects.filter(pk=self.left.pk).values().get())
        self.assertEqual(after.pop("trainer_id"), self.b.trainer.pk)
        before.pop("trainer_id")
        self.assertEqual(before, after)
        self.assertEqual(fresh_owned(self.right.pk).trainer_id, self.a.trainer.pk)
        self.assertEqual(len(receipt["pokemon"]), 2)
        self.assertFalse(operation.reservations.exists())
        self.assertEqual(ActiveMoveslot.objects.get(pk=slot.pk).current_pp, 2)
        self.assertEqual(MovePPBoost.objects.get(pk=boost.pk).bonus_pp, 6)
        self.assertEqual(PokemonLearnedMove.objects.get(pk=learned.pk).pokemon_id, self.left.pk)

    def test_exact_prepare_commit_replay_and_released_asset_not_resurrected(self):
        request = uuid4()
        moves = [{"pokemon": self.left.pk, "source": self.a.pk, "destination": self.b.pk}]
        operation = self.service.prepare(self.b.pk, moves, request_id=request)
        self.assertEqual(self.service.prepare(self.b.pk, moves, request_id=request).pk, operation.pk)
        with self.assertRaisesRegex(OwnershipError, "different"):
            self.service.prepare(self.b.pk, [{**moves[0], "mode": "box"}], request_id=request)
        OwnershipTransfers(self.b).approve(operation.pk)
        first = self.service.commit(operation.pk)
        PlacementService(UserStorage.objects.get(user=self.b)).release(fresh_owned(self.left.pk))
        self.assertEqual(self.service.commit(operation.pk), first)
        self.assertFalse(OwnedPokemon.objects.filter(pk=self.left.pk).exists())

    def test_foreign_character_cannot_approve_cancel_commit_or_offer_assets(self):
        operation = self.offer()
        # Same-account ownership is deliberately irrelevant: only actor.pk is used.
        for method in ("approve", "cancel", "commit"):
            with self.assertRaises(OwnershipError):
                getattr(OwnershipTransfers(self.c), method)(operation.pk)
        with self.assertRaises(PlacementError):
            OwnershipTransfers(self.c).prepare(self.b.pk, [
                {"pokemon": self.left.pk, "source": self.c.pk, "destination": self.b.pk}])

    def test_reservation_blocks_storage_release_fusion_and_second_offer(self):
        operation = self.offer()
        placement = PlacementService(UserStorage.objects.get(user=self.a))
        for action in (lambda: placement.to_box(self.left), lambda: placement.to_party(self.left, 4),
                       lambda: placement.release(self.left), lambda: placement.reserve_for_fusion(self.left),
                       lambda: self.offer()):
            with self.assertRaisesRegex(PlacementError, "reserved"):
                action()
        self.service.cancel(operation.pk)
        placement.to_box(self.left)

    def test_nontrade_reservations_block_offers_and_placement(self):
        for kind in ("market", "daycare", "breeding"):
            reservation = PokemonReservation.objects.create(pokemon=self.left,
                storage=UserStorage.objects.get(user=self.a), kind=kind, token=uuid4())
            with self.assertRaisesRegex(PlacementError, "reserved"):
                self.offer()
            with self.assertRaisesRegex(PlacementError, "reserved"):
                PlacementService(reservation.storage).to_box(self.left)
            reservation.delete()

    def test_system_reservation_api_binds_owner_kind_and_cycle(self):
        """The next systems share one claim route without granting foreign custody."""
        token = uuid4()
        service = PokemonReservations(self.a)
        first = service.claim("market", [self.left.pk], token)
        self.assertEqual(service.claim("market", [self.left.pk], token)[0].pk, first[0].pk)
        with self.assertRaises(PlacementError):
            PokemonReservations(self.b).claim("market", [self.left.pk], token)
        with self.assertRaises(PlacementError):
            service.claim("breeding", [self.left.pk], token)
        self.assertEqual(PokemonReservations(self.b).release("market", token), 0)
        self.assertEqual(service.release("market", uuid4()), 0)
        self.assertEqual(service.release("market", token), 1)
        self.assertEqual(service.release("market", token), 0)

    def test_active_and_unlocked_fusion_references_and_battle_block(self):
        for key, value in (("fusion_id", str(self.left.pk)), ("fusion_forms", [str(self.left.pk)]),
                           ("battle_id", "a saved battle"), ("battle_lock", 0)):
            self.a.attributes.add(key, value)
            try:
                with self.assertRaises(PlacementError):
                    self.offer()
            finally:
                self.a.attributes.remove(key)
        PlacementService(UserStorage.objects.get(user=self.a)).reserve_for_fusion(self.left)
        with self.assertRaisesRegex(OwnershipError, "Fusion"):
            self.offer()

    def test_fresh_battle_state_at_commit_is_rechecked(self):
        operation = self.offer()
        OwnershipTransfers(self.b).approve(operation.pk)
        self.b.attributes.add("battle_lock", "new battle")
        try:
            with self.assertRaisesRegex(OwnershipError, "battle"):
                self.service.commit(operation.pk)
        finally:
            self.b.attributes.remove("battle_lock")
        self.assertEqual(fresh_owned(self.left.pk).trainer_id, self.a.trainer.pk)
        self.assertTrue(operation.reservations.exists())

    def test_use_player_route_rejects_reserved_target_without_consuming(self):
        """The existing field medicine boundary receives the shared reservation guard."""
        import evennia
        from evennia.commands.command import Command

        with patch.object(evennia, "Command", Command):
            from commands.player.cmd_inventory import CmdUseItem
        operation = self.offer()
        self.a.trainer.add_item("Potion", 1)
        before = OwnedPokemon.objects.filter(pk=self.left.pk).values().get()
        messages = []
        with patch.object(self.a, "msg", side_effect=messages.append):
            command = CmdUseItem()
            command.caller, command.args = self.a, "Potion=1"
            command.parse()
            command.func()
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.left.pk).values().get(), before)
        self.assertEqual(self.a.trainer.get_item_quantity("Potion"), 1)
        self.assertTrue(any("eligible owned party member" in message for message in messages), messages)
        self.service.cancel(operation.pk)

    def test_battle_admission_and_transfer_share_storage_serialization(self):
        """A pending party offer cannot enter battle; committed transfers are fresh."""
        from utils.locks import clear_battle_lock, set_battle_lock

        operation = self.offer()
        with self.assertRaisesRegex(PlacementError, "reserved"):
            set_battle_lock(self.a, str(uuid4()))
        self.assertIsNone(self.a.db.battle_lock)
        self.service.cancel(operation.pk)
        battle_id = str(uuid4())
        set_battle_lock(self.a, battle_id)
        try:
            with self.assertRaisesRegex(PlacementError, "battle"):
                self.offer()
        finally:
            clear_battle_lock(self.a)

    def test_battle_admission_vs_offer_never_grants_both(self):
        """Independent connections cannot start a party battle and reserve its asset."""
        from utils.locks import clear_battle_lock, set_battle_lock

        outcomes = self.race(lambda: self.offer(), lambda: set_battle_lock(self.a, str(uuid4())))
        self.assertEqual(sum(isinstance(value, PlacementError) for value in outcomes), 1)
        clear_battle_lock(self.a)

    def test_outer_rollback_does_not_publish_a_completed_transfer(self):
        """Compound callers can roll back a successful service savepoint and retry."""
        operation = self.offer()
        OwnershipTransfers(self.b).approve(operation.pk)
        with self.assertRaisesRegex(RuntimeError, "outer"), transaction.atomic():
            self.service.commit(operation.pk)
            raise RuntimeError("outer failure")
        self.assertEqual(fresh_owned(self.left.pk).trainer_id, self.a.trainer.pk)
        self.assertEqual(OwnershipTransfer.objects.get(pk=operation.pk).state, "pending")
        self.assertEqual(self.service.commit(operation.pk)["pokemon"][0]["owner"], self.b.pk)

    def test_full_party_auto_boxes_and_explicit_party_failure_is_atomic(self):
        for _ in range(6):
            self.mon(self.b)
        operation = self.offer(mode="party")
        OwnershipTransfers(self.b).approve(operation.pk)
        with self.assertRaisesRegex(PlacementError, "six"):
            self.service.commit(operation.pk)
        self.assertEqual(fresh_owned(self.left.pk).trainer_id, self.a.trainer.pk)
        self.service.cancel(operation.pk)
        operation = self.offer()
        OwnershipTransfers(self.b).approve(operation.pk)
        receipt = self.service.commit(operation.pk)
        self.assertEqual(receipt["pokemon"][0]["location"], "box")

    def test_full_party_swap_frees_outgoing_slots_before_incoming_allocation(self):
        PlacementService(UserStorage.objects.get(user=self.b)).to_party(self.right)
        for _ in range(5):
            self.mon(self.a)
            self.mon(self.b)
        operation = self.offer(swap=True)
        OwnershipTransfers(self.b).approve(operation.pk)
        self.assertEqual({row["location"] for row in self.service.commit(operation.pk)["pokemon"]}, {"party"})

    def test_failure_after_first_transfer_rolls_back_both_and_retains_approval(self):
        operation = self.offer(swap=True)
        OwnershipTransfers(self.b).approve(operation.pk)
        original = PlacementService._party
        calls = []
        def fail_second(service, *args, **kwargs):
            """Inject a write failure after the first destination was written."""
            calls.append(1)
            if len(calls) == 2:
                raise RuntimeError("injected second destination fault")
            return original(service, *args, **kwargs)
        with patch.object(PlacementService, "_party", fail_second):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                self.service.commit(operation.pk)
        self.assertEqual(fresh_owned(self.left.pk).trainer_id, self.a.trainer.pk)
        self.assertEqual(fresh_owned(self.right.pk).trainer_id, self.b.trainer.pk)
        self.assertEqual(operation.reservations.count(), 2)
        self.assertEqual(OwnershipTransfer.objects.get(pk=operation.pk).state, "pending")
        self.assertEqual(len(self.service.commit(operation.pk)["pokemon"]), 2)

    def test_stale_identity_map_cannot_grant_foreign_custody(self):
        operation = self.offer()
        OwnershipTransfers(self.b).approve(operation.pk)
        self.service.commit(operation.pk)
        self.left.trainer = self.a.trainer  # stale retained client-side instance
        with self.assertRaisesRegex(PlacementError, "belong"):
            PlacementService(UserStorage.objects.get(user=self.a)).release(self.left)

    def test_expiry_cancel_and_terminal_receipt_are_safe(self):
        start = timezone.now()
        service = OwnershipTransfers(self.a, clock=lambda: start)
        moves = [{"pokemon": self.left.pk, "source": self.a.pk, "destination": self.b.pk}]
        operation = service.prepare(self.b.pk, moves)
        later = OwnershipTransfers(self.b, clock=lambda: start + timedelta(hours=1))
        with self.assertRaisesRegex(OwnershipError, "expired"):
            later.approve(operation.pk)
        self.assertEqual(later.cancel(operation.pk).state, "expired")
        self.assertFalse(operation.reservations.exists())
        self.assertEqual(service.cancel(operation.pk).state, "expired")

    def race(self, *operations):
        """Start independent connections together; return accepted/rejected outcomes."""
        barrier = Barrier(len(operations))
        def worker(operation):
            try:
                barrier.wait(timeout=10)
                return operation()
            except PlacementError as error:
                return error
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(operations)) as pool:
            return list(pool.map(worker, operations))

    def test_independent_duplicate_commit_returns_same_receipt(self):
        operation = self.offer(swap=True)
        OwnershipTransfers(self.b).approve(operation.pk)
        outcomes = self.race(lambda: self.service.commit(operation.pk),
                             lambda: OwnershipTransfers(self.b).commit(operation.pk))
        self.assertEqual(outcomes[0], outcomes[1])
        self.assertEqual(OwnershipTransfer.objects.filter(pk=operation.pk, state="completed").count(), 1)

    def test_transfer_vs_release_deposit_withdraw_and_cancel(self):
        for mutation in ("release", "to_box", "to_party", "cancel"):
            if not OwnedPokemon.objects.filter(pk=self.left.pk).exists():
                self.left = self.mon(self.a)
            operation = self.offer()
            OwnershipTransfers(self.b).approve(operation.pk)
            service = PlacementService(UserStorage.objects.get(user=self.a))
            action = (lambda: self.service.cancel(operation.pk)) if mutation == "cancel" else (
                lambda: getattr(service, mutation)(self.left))
            self.race(lambda: self.service.commit(operation.pk), action)
            state = OwnershipTransfer.objects.get(pk=operation.pk).state
            self.assertIn(state, ("completed", "cancelled"))
            self.assertEqual(fresh_owned(self.left.pk).trainer_id,
                             self.b.trainer.pk if state == "completed" else self.a.trainer.pk)
            if state == "completed":
                self.left = self.mon(self.a)

    def test_two_transfer_destinations_cannot_reserve_same_asset(self):
        outcomes = self.race(lambda: self.offer(), lambda: self.service.prepare(self.c.pk, [
            {"pokemon": self.left.pk, "source": self.a.pk, "destination": self.c.pk}]))
        self.assertEqual(sum(isinstance(value, PlacementError) for value in outcomes), 1)
        self.assertEqual(PokemonReservation.objects.filter(pokemon=self.left).count(), 1)

    def test_last_destination_slot_contention_boxes_exactly_one(self):
        for _ in range(5):
            self.mon(self.b)
        third = self.mon(self.c)
        first = self.offer()
        second = OwnershipTransfers(self.c).prepare(self.b.pk, [
            {"pokemon": third.pk, "source": self.c.pk, "destination": self.b.pk}])
        OwnershipTransfers(self.b).approve(first.pk)
        OwnershipTransfers(self.b).approve(second.pk)
        outcomes = self.race(lambda: self.service.commit(first.pk),
                             lambda: OwnershipTransfers(self.c).commit(second.pk))
        self.assertEqual(sorted(value["pokemon"][0]["location"] for value in outcomes), ["box", "party"])

    def test_database_rejects_reservation_owner_mismatch_and_fusion_move(self):
        for update in ({"storage": UserStorage.objects.get(user=self.c)},):
            with self.assertRaises(IntegrityError), transaction.atomic():
                PokemonReservation.objects.create(pokemon=self.left, kind="market", token=uuid4(), **update)
        operation = self.offer()
        with self.assertRaises(IntegrityError), transaction.atomic():
            PokemonPlacement.objects.filter(pokemon=self.left).update(location_type="fusion", slot=None)
        self.service.cancel(operation.pk)

    def test_database_seals_terms_and_completed_receipts(self):
        operation = self.offer()
        with self.assertRaises(IntegrityError), transaction.atomic():
            OwnershipTransfer.objects.filter(pk=operation.pk).update(terms=[])
        OwnershipTransfers(self.b).approve(operation.pk)
        self.service.commit(operation.pk)
        with self.assertRaises(IntegrityError), transaction.atomic():
            OwnershipTransfer.objects.filter(pk=operation.pk).update(result={})


if __name__ == "__main__":
    try:
        database.create_model_tables()
        ContentType.objects.get_for_models(*apps.get_models(), for_concrete_models=False)
        with connection.schema_editor() as editor:
            importlib.import_module("pokemon.migrations.0041_placement_integrity_triggers").install(apps, editor)
            importlib.import_module("pokemon.migrations.0048_ownership_integrity").install(apps, editor)
        unittest.main(verbosity=2)
    finally:
        database.close()

"""Real PostgreSQL reward recovery and concurrency checks, outside legacy stubs.

Run with python tests/integration/recovery_cases.py and an explicit
PF2_TEST_POSTGRES_DSN. All writes use a randomly named, disposable schema.
Production tables are built directly; this command does not run migrations.
"""

from __future__ import annotations

import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from time import monotonic
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres


class RecoveryCases(unittest.TestCase):
    """Exercise production services, persisted retries, and competing writers."""

    def setUp(self):
        """Give every case two ordinary characters sharing one account."""
        self.account = AccountDB.objects.create(username="recovery-" + uuid4().hex)
        self.player = ObjectDB.objects.create(db_key="Player A", db_account=self.account)
        self.other = ObjectDB.objects.create(db_key="Player B", db_account=self.account)
        number = Trainer.objects.count() + 1
        self.trainer = Trainer.objects.create(user=self.player, trainer_number=number)
        self.other_trainer = Trainer.objects.create(user=self.other, trainer_number=number + 1)
        self.badge = GymBadge.objects.create(name="Recovery Badge", region="Integration")
        self.metadata = {"source_type": "gym_leader", "badge_id": self.badge.pk, "gym_key": "recovery"}

    def completed_run(self):
        """Persist an eligible completed Adventure for the current character."""
        return AdventureSession.objects.create(
            leader=self.player, template_key="alpha_meadow", current_node="entrance",
            state="completed", completed_at=timezone.now(),
        )

    def fresh_rewards(self):
        """Construct a service from a newly fetched character, as after reconnect."""
        return GymVictoryRewards(ObjectDB.objects.get(pk=self.player.pk))

    def race(self, *actions):
        """Start competing production calls on distinct PostgreSQL connections."""
        barrier = Barrier(len(actions))

        def run(action):
            close_old_connections()
            try:
                connection.ensure_connection()
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    pid = cursor.fetchone()[0]
                barrier.wait(timeout=10)
                return pid, action()
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            futures = [pool.submit(run, action) for action in actions]
            results = [future.result(timeout=30) for future in futures]
        self.assertEqual(len({pid for pid, _result in results}), len(actions))
        return [result for _pid, result in results]

    def test_duplicate_gym_claims_award_once(self):
        """Two simultaneous claims for one receipt commit one badge delivery."""
        victory = self.fresh_rewards().record(uuid4(), self.metadata)
        results = self.race(
            lambda: self.fresh_rewards().claim(victory.pk),
            lambda: self.fresh_rewards().claim(victory.pk),
        )
        self.assertTrue(all(result.completed for result in results))
        self.assertEqual(sum(result.awarded for result in results), 1)
        self.assertEqual(self.trainer.badges.count(), 1)
        victory.refresh_from_db()
        self.assertIsNotNone(victory.claimed_at)

    def test_overlapping_rematch_claims_award_once(self):
        """Different victories awarding the same badge share the character lock."""
        first = self.fresh_rewards().record(uuid4(), self.metadata)
        second = self.fresh_rewards().record(uuid4(), self.metadata)
        results = self.race(
            lambda: self.fresh_rewards().claim(first.pk),
            lambda: self.fresh_rewards().claim(second.pk),
        )
        self.assertTrue(all(result.completed for result in results))
        self.assertEqual(sum(result.awarded for result in results), 1)
        self.assertEqual(self.trainer.badges.count(), 1)
        self.assertEqual(GymVictory.objects.filter(player=self.player, claimed_at__isnull=False).count(), 2)

    def test_duplicate_victory_record_keeps_original_metadata(self):
        """Replayed callbacks create one ledger row and retain its first snapshot."""
        victory_id = uuid4()
        results = self.race(
            lambda: self.fresh_rewards().record(victory_id, self.metadata),
            lambda: self.fresh_rewards().record(victory_id, self.metadata),
        )
        self.assertEqual([result.pk for result in results], [victory_id, victory_id])
        self.fresh_rewards().record(victory_id, {**self.metadata, "badge_id": -1})
        self.assertEqual(GymVictory.objects.get(pk=victory_id).metadata, self.metadata)

    def test_gym_claim_waits_for_character_row_lock(self):
        """Observe a real PostgreSQL lock wait before allowing badge delivery."""
        victory = self.fresh_rewards().record(uuid4(), self.metadata)
        started = Event()
        worker_pid = []

        def claim():
            close_old_connections()
            try:
                connection.ensure_connection()
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    worker_pid.append(cursor.fetchone()[0])
                started.set()
                return self.fresh_rewards().claim(victory.pk)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                ObjectDB.objects.select_for_update().get(pk=self.player.pk)
                future = pool.submit(claim)
                self.assertTrue(started.wait(timeout=5))
                waiting = False
                deadline = monotonic() + 5
                while monotonic() < deadline and not future.done():
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT pg_stat_clear_snapshot()")
                        cursor.execute("SELECT wait_event_type FROM pg_stat_activity WHERE pid = %s", worker_pid)
                        row = cursor.fetchone()
                    if row and row[0] == "Lock":
                        waiting = True
                        break
                    Event().wait(0.01)
                self.assertTrue(waiting, "Claim did not wait for the held character row lock.")
                self.assertFalse(future.done())
            self.assertTrue(future.result(timeout=15).awarded)

    def test_gym_write_and_marker_failures_roll_back(self):
        """Real badge writes roll back with failed delivery or claim markers."""
        victory = self.fresh_rewards().record(uuid4(), self.metadata)
        original_add = Trainer.add_badge
        original_save = GymVictory.save

        def fail_badge(trainer, badge):
            original_add(trainer, badge)
            raise RuntimeError("injected badge delivery failure")

        def fail_marker(receipt, *args, **kwargs):
            if "claimed_at" in kwargs.get("update_fields", ()):
                raise RuntimeError("injected gym marker failure")
            return original_save(receipt, *args, **kwargs)

        for target, method, failure in (
            (Trainer, "add_badge", fail_badge), (GymVictory, "save", fail_marker),
        ):
            with patch.object(target, method, failure):
                with self.assertRaises(RuntimeError):
                    self.fresh_rewards().claim(victory.pk)
            victory.refresh_from_db()
            self.assertIsNone(victory.claimed_at)
            self.assertEqual(self.trainer.badges.count(), 0)
        self.assertTrue(self.fresh_rewards().claim(victory.pk).awarded)

    def test_duplicate_adventure_completion_awards_once(self):
        """Two callbacks for the same run create one Potion and one claim marker."""
        run = self.completed_run()
        results = self.race(
            lambda: progress.finalize_completion(AdventureSession.objects.get(pk=run.pk)),
            lambda: progress.finalize_completion(AdventureSession.objects.get(pk=run.pk)),
        )
        self.assertEqual(sum(claimed for claimed, _message in results), 1)
        self.assertEqual(self.trainer.get_item_quantity("Potion"), 1)
        self.assertEqual(AdventureParticipation.objects.filter(session=run).count(), 1)

    def test_overlapping_adventure_first_clears_award_once(self):
        """Concurrent completed runs agree on a single first-clear entitlement."""
        first, second = self.completed_run(), self.completed_run()
        results = self.race(
            lambda: progress.finalize_completion(AdventureSession.objects.get(pk=first.pk)),
            lambda: progress.finalize_completion(AdventureSession.objects.get(pk=second.pk)),
        )
        self.assertEqual(sum(claimed for claimed, _message in results), 1)
        self.assertEqual(self.trainer.get_item_quantity("Potion"), 1)
        receipts = AdventureParticipation.objects.filter(player=self.player)
        self.assertEqual(receipts.count(), 2)
        self.assertEqual(receipts.filter(reward_claimed_at__isnull=False).count(), 1)

    def test_adventure_retry_after_write_and_marker_failures(self):
        """Failed item writes remain unpaid and overlapping recovery pays once."""
        run = self.completed_run()
        original_add = Trainer.add_item
        original_save = AdventureParticipation.save

        def fail_item(trainer, item, amount=1):
            original_add(trainer, item, amount)
            raise RuntimeError("injected item delivery failure")

        def fail_marker(receipt, *args, **kwargs):
            if "reward_claimed_at" in kwargs.get("update_fields", ()):
                raise RuntimeError("injected Adventure marker failure")
            return original_save(receipt, *args, **kwargs)

        for target, method, failure in (
            (Trainer, "add_item", fail_item), (AdventureParticipation, "save", fail_marker),
        ):
            with patch.object(target, method, failure):
                self.assertFalse(progress.finalize_completion(AdventureSession.objects.get(pk=run.pk))[0])
            self.assertEqual(self.trainer.get_item_quantity("Potion"), 0)
            self.assertIsNone(AdventureParticipation.objects.get(session=run).reward_claimed_at)
        self.race(
            lambda: progress.claim_completed_rewards(ObjectDB.objects.get(pk=self.player.pk)),
            lambda: progress.claim_completed_rewards(ObjectDB.objects.get(pk=self.player.pk)),
        )
        self.assertEqual(self.trainer.get_item_quantity("Potion"), 1)
        self.assertIsNotNone(AdventureParticipation.objects.get(session=run).reward_claimed_at)

    def test_same_account_characters_cannot_claim_each_others_rewards(self):
        """Account sharing does not share gym or Adventure entitlements."""
        victory = self.fresh_rewards().record(uuid4(), self.metadata)
        with self.assertRaises(GymVictory.DoesNotExist):
            GymVictoryRewards(self.other).claim(victory.pk)
        self.assertEqual(GymVictoryRewards(self.other).claim_pending(), ())
        run = self.completed_run()
        with patch.object(Trainer, "add_item", side_effect=RuntimeError("temporarily unavailable")):
            self.assertFalse(progress.finalize_completion(run)[0])
        self.assertEqual(progress.claim_completed_rewards(self.other), "No unclaimed Adventure rewards.")
        self.assertEqual(self.other_trainer.get_item_quantity("Potion"), 0)
        self.assertEqual(self.other_trainer.badges.count(), 0)
        self.assertIn("Potion x1", progress.claim_completed_rewards(ObjectDB.objects.get(pk=self.player.pk)))


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        from django.db import close_old_connections, connection, connections, transaction
        from django.utils import timezone
        from evennia.accounts.models import AccountDB
        from evennia.objects.models import ObjectDB

        from pokemon.adventures import progress
        from pokemon.models.adventures import AdventureParticipation, AdventureSession
        from pokemon.models.gym import GymVictory
        from pokemon.models.trainer import GymBadge, Trainer
        from pokemon.services.gym_rewards import GymVictoryRewards

        unittest.main(verbosity=2)

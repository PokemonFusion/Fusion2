"""Issue #833 production admission/privacy commands and independent SQL races."""

from __future__ import annotations

import importlib
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres


class AdventurePrivacyCases(unittest.TestCase):
    """Exercise fixed-pool reservations using actual character/room persistence."""

    def setUp(self):
        """Build two ordinary players, including two characters on one account."""
        suffix = uuid4().hex[:10]
        self.hall = ObjectDB.objects.create(db_key="Privacy Hall " + suffix,
                                            db_typeclass_path="typeclasses.rooms.FusionRoom")
        self.hall.db.adventure_hall = True
        self.rooms = [ObjectDB.objects.create(db_key="Privacy Instance " + suffix + str(i),
                     db_typeclass_path="typeclasses.rooms.FusionRoom") for i in range(2)]
        for room in self.rooms:
            room.db.adventure_instance = True
        self.hall.db.adventure_instance_rooms = self.rooms[:1]
        self.account = AccountDB.objects.create(username="Privacy" + suffix)
        self.account.permissions.add("Player")
        self.players = []
        for i in range(3):
            player = ObjectDB.objects.create(db_key="PrivacyPlayer" + suffix + str(i),
                                            db_typeclass_path="pokemon.user.User",
                                            db_location=self.hall,
                                            db_account=self.account if i < 2 else None)
            player.permissions.add("Player")
            player.location = self.hall
            Trainer.objects.get_or_create(user=player, defaults={"trainer_number": Trainer.objects.count() + 1})
            self.players.append(player)
        self.messages = []
        self.transport = patch.object(type(self.players[0]), "msg", lambda obj, text=None, **kw: self.messages.append((obj.pk, str(text))))
        self.transport.start()
        self.addCleanup(self.transport.stop)

    def start(self, player=None):
        """Start through the production command and return the persisted claim."""
        player = player or self.players[0]
        command = CmdAdventure()
        command.caller = player
        command.args = "alpha_meadow"
        command.switches = ["start"]
        command.func()
        self.assertTrue(AdventureSession.objects.filter(leader=player, holds_instance=True).exists(), self.messages[-5:])
        return AdventureSession.objects.get(leader=player, holds_instance=True)

    def race(self, operations):
        """Synchronize independent connections; retain every result and exception."""
        barrier = Barrier(len(operations))

        def run(operation):
            from django.db import connection, connections

            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    backend = cursor.fetchone()[0]
                barrier.wait(timeout=10)
                return backend, operation()
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(operations)) as executor:
            futures = [executor.submit(run, operation) for operation in operations]
            results = [future.result(timeout=30) for future in futures]
        self.assertEqual(len({backend for backend, _result in results}), len(operations))
        return [result for _backend, result in results]

    def test_same_room_race_has_one_owner(self):
        """Competing starts never assign one room to two characters."""
        results = self.race([lambda p=p: sessions.start_session(p, "alpha_meadow") for p in self.players[:2]])
        self.assertEqual(sum(result.ok for result in results), 1, [result.message for result in results])
        self.assertEqual(AdventureSession.objects.filter(holds_instance=True, instance_room=self.rooms[0]).count(), 1)
        self.assertIn("try again", next(result.message.lower() for result in results if not result.ok))

    def test_same_character_race_has_one_run(self):
        """Extra room capacity cannot give one character simultaneous runs."""
        self.hall.db.adventure_instance_rooms = self.rooms
        results = self.race([lambda: sessions.start_session(self.players[0], "alpha_meadow")] * 2)
        self.assertEqual(sum(result.ok for result in results), 1, [result.message for result in results])
        self.assertEqual(AdventureSession.objects.filter(holds_instance=True, leader=self.players[0]).count(), 1)

    def test_database_rejects_duplicate_room_and_character(self):
        """Uniqueness remains enforced independently of cooperative service locks."""
        session = self.start()
        from django.db import IntegrityError, transaction

        for leader, room in ((self.players[1], self.rooms[0]), (self.players[0], self.rooms[1])):
            with self.assertRaises(IntegrityError), transaction.atomic():
                AdventureSession.objects.create(leader=leader, instance_room=room, holds_instance=True,
                                                 template_key="alpha_meadow", current_node="entrance")
        self.assertEqual(AdventureSession.objects.get(pk=session.pk).holds_instance, True)

    def test_lost_markers_cannot_reassign_room(self):
        """Persisted occupancy survives lost room and character caches."""
        session = self.start()
        self.players[0].attributes.remove("adventure_session_id")
        self.rooms[0].attributes.remove("adventure_session_id")
        result = sessions.start_session(self.players[1], "alpha_meadow")
        self.assertFalse(result.ok)
        self.assertEqual(sessions.get_current_session_for_player(self.players[0]).pk, session.pk)
        self.assertTrue(AdventurePrivacy.room_access(self.rooms[0], self.players[0]))

    def test_borrowed_pointer_and_reconnect_do_not_grant_admission(self):
        """Same-account and other-account outsiders cannot borrow session identity."""
        session = self.start()
        for outsider in self.players[1:]:
            outsider.db.adventure_session_id = session.pk
            self.assertIsNone(sessions.sync_player_to_active_session(outsider))
            self.assertEqual(outsider.location.pk, self.hall.pk)
            self.assertFalse(outsider.move_to(self.rooms[0], quiet=True))
            self.assertEqual(outsider.location.pk, self.hall.pk)
            self.assertEqual(self.rooms[0].return_appearance(outsider), PRIVATE_MESSAGE)
            self.assertFalse(AdventurePrivacy.room_access(self.rooms[0], outsider))

    def test_normal_exit_cannot_enter_foreign_instance(self):
        """The original public instance exit remains protected at the destination."""
        self.start()
        exit_obj = ObjectDB.objects.create(db_key="instance", db_location=self.hall,
                    db_destination=self.rooms[0], db_typeclass_path="typeclasses.exits.Exit")
        exit_obj.at_traverse(self.players[1], self.rooms[0])
        self.assertEqual(self.players[1].location.pk, self.hall.pk)

    def test_legacy_numeric_room_flag_protects_admission(self):
        """An existing numeric room tag gets the same reservation/privacy contract."""
        self.rooms[0].db.adventure_instance = 1
        self.start()
        self.assertFalse(self.players[1].move_to(self.rooms[0], quiet=True))
        self.assertEqual(self.players[1].location.pk, self.hall.pk)

    def test_completed_occupancy_survives_cleanup_and_reconnect(self):
        """Completion does not recycle the room or lose the owner's current run."""
        session = self.start()
        session.state = "completed"
        session.save(update_fields=["state"])
        from world.stale_state import cleanup_stale_state

        cleanup_stale_state(objects=[self.players[0], self.rooms[0]], active_battle_ids=set())
        self.players[0].attributes.remove("adventure_session_id")
        self.assertEqual(sessions.sync_player_to_active_session(self.players[0]).pk, session.pk)
        self.assertFalse(sessions.room_is_available(self.rooms[0]))
        self.assertTrue(sessions.leave_session(self.players[0]).ok)
        session.refresh_from_db()
        self.assertFalse(session.holds_instance)
        self.assertEqual(session.state, "completed")

    def test_rejected_start_releases_only_new_reservation(self):
        """A failed entry permits another player to use that room normally."""
        with patch.object(type(self.players[0]), "move_to", return_value=False):
            result = sessions.start_session(self.players[0], "alpha_meadow")
        self.assertFalse(result.ok)
        self.assertFalse(AdventureSession.objects.filter(leader=self.players[0], holds_instance=True).exists())
        self.assertEqual(self.start(self.players[1]).instance_room_id, self.rooms[0].pk)

    def test_failed_creation_rolls_back_the_claim(self):
        """An exception after session insertion leaves neither a run nor a room claim."""
        from pokemon.adventures import progress

        with patch.object(progress, "safe_ensure_participation", side_effect=RuntimeError("fixture creation failure")):
            with self.assertRaisesRegex(RuntimeError, "fixture creation failure"):
                sessions.start_session(self.players[0], "alpha_meadow")
        self.assertFalse(AdventureSession.objects.filter(leader=self.players[0]).exists())
        replacement = self.start(self.players[1])
        self.assertEqual(replacement.instance_room_id, self.rooms[0].pk)
        self.assertEqual(self.rooms[0].db.adventure_session_id, replacement.pk)

    def test_rejected_return_retains_reservation(self):
        """Neither leave nor expiry releases an owner stranded by failed movement."""
        session = self.start()
        with patch.object(type(self.players[0]), "move_to", return_value=False):
            self.assertFalse(sessions.leave_session(self.players[0]).ok)
            self.assertFalse(sessions.expire_session(session))
        session.refresh_from_db()
        self.assertTrue(session.holds_instance)
        self.assertFalse(sessions.room_is_available(self.rooms[0]))

    def staff_command(self, action, session):
        """Dispatch a permission-checked recovery command, separate from Player play."""
        command = CmdAdventureAdmin()
        command.caller = self.players[2]
        command.caller.permissions.add("Wizards")
        self.assertTrue(command.access(command.caller, "cmd"))
        self.assertFalse(command.access(self.players[0], "cmd"))
        command.switches = [action]
        command.args = str(session.pk) if action == "abort" else session.leader.key
        with patch.object(command.caller, "search", return_value=session.leader):
            command.func()

    def test_staff_recovery_releases_both_claims_and_allows_restart(self):
        """Abort and return free the room and the same character's unique run slot."""
        for action in ("abort", "return"):
            with self.subTest(action=action):
                session = self.start()
                self.staff_command(action, session)
                session.refresh_from_db()
                self.assertFalse(session.holds_instance)
                self.assertEqual(session.state, "abandoned")
                self.assertEqual(self.players[0].location.pk, self.hall.pk)
                self.assertFalse(self.players[0].db.adventure_session_id)
                self.assertFalse(self.rooms[0].db.adventure_session_id)
                self.assertFalse(self.players[0].cmdset.has_cmdset(AdventureMovementCmdSet, must_be_default=False))
                self.start()
                self.assertTrue(sessions.leave_session(self.players[0]).ok)
                self.start(self.players[1])
                self.assertTrue(sessions.leave_session(self.players[1]).ok)

    def test_staff_completed_recovery_preserves_unpaid_results(self):
        """Releasing completed occupancy changes no result or unpaid reward record."""
        from django.utils import timezone

        for action in ("abort", "return"):
            with self.subTest(action=action):
                session = self.start()
                AdventureSession.objects.filter(pk=session.pk).update(state="completed", completed_at=timezone.now())
                AdventureParticipation.objects.filter(session=session).update(
                    completed_at=timezone.now(), encounter_result="capture", reward_item="Potion", reward_amount=1)
                before = list(AdventureParticipation.objects.filter(session=session).values())
                self.staff_command(action, session)
                session.refresh_from_db()
                self.assertEqual(session.state, "completed")
                self.assertFalse(session.holds_instance)
                self.assertEqual(list(AdventureParticipation.objects.filter(session=session).values()), before)
                self.assertEqual(self.players[0].trainer.get_item_quantity("Potion"), 0)

    def test_staff_rejected_return_retains_claim_and_movement(self):
        """Staff movement failures keep the persisted run, markers and cardinal commands."""
        for action in ("abort", "return"):
            with self.subTest(action=action):
                session = self.start()
                before = list(AdventureSession.objects.filter(pk=session.pk).values())
                with patch.object(self.players[0], "move_to", return_value=False):
                    self.staff_command(action, session)
                self.assertEqual(list(AdventureSession.objects.filter(pk=session.pk).values()), before)
                self.assertEqual(self.players[0].location.pk, self.rooms[0].pk)
                self.assertEqual(self.players[0].db.adventure_session_id, session.pk)
                self.assertEqual(self.rooms[0].db.adventure_session_id, session.pk)
                self.assertTrue(self.players[0].cmdset.has_cmdset(AdventureMovementCmdSet, must_be_default=False))
                self.assertIn("blocked", self.messages[-1][1])
                self.staff_command(action, session)

    def test_staff_completed_recovery_survives_marker_loss(self):
        """The database occupancy claim remains visible and recoverable without pointers."""
        for action in ("abort", "return"):
            with self.subTest(action=action):
                session = self.start()
                AdventureSession.objects.filter(pk=session.pk).update(state="completed")
                self.players[0].attributes.remove("adventure_session_id")
                self.rooms[0].attributes.remove("adventure_session_id")
                self.staff_command(action, session)
                session.refresh_from_db()
                self.assertFalse(session.holds_instance)
                self.assertEqual(session.state, "completed")
                self.assertEqual(self.players[0].location.pk, self.hall.pk)

    def test_staff_hall_fallback_releases_claim_without_rewriting_history(self):
        """The validated fallback destination shares the same atomic release path."""
        from commands.admin import cmd_adventureadmin

        for action in ("abort", "return"):
            with self.subTest(action=action):
                session = self.start()
                AdventureSession.objects.filter(pk=session.pk).update(return_location=None)
                with patch.object(cmd_adventureadmin, "_find_adventure_hall", return_value=self.hall):
                    self.staff_command(action, session)
                session.refresh_from_db()
                self.assertFalse(session.holds_instance)
                self.assertIsNone(session.return_location_id)
                self.assertEqual(self.players[0].location.pk, self.hall.pk)

    def test_stale_staff_abort_preserves_new_room_owner(self):
        """A delayed abort of a released ID cannot clear its replacement reservation."""
        old = self.start()
        self.staff_command("abort", old)
        newer = self.start()
        before = list(AdventureSession.objects.filter(pk=newer.pk).values())
        self.staff_command("abort", old)
        self.assertEqual(list(AdventureSession.objects.filter(pk=newer.pk).values()), before)
        self.assertEqual(self.players[0].location.pk, self.rooms[0].pk)
        self.assertEqual(self.players[0].db.adventure_session_id, newer.pk)
        self.assertEqual(self.rooms[0].db.adventure_session_id, newer.pk)

    def test_old_cleanup_cannot_release_new_run(self):
        """Old leave/expiry calls cannot move or unreserve the replacement owner."""
        old = self.start()
        self.assertTrue(sessions.leave_session(self.players[0]).ok)
        newer = self.start()
        self.assertFalse(sessions.leave_session(self.players[0], session=old).ok)
        self.assertFalse(sessions.expire_session(old))
        self.assertEqual(self.players[0].location.pk, self.rooms[0].pk)
        self.assertEqual(self.players[0].db.adventure_session_id, newer.pk)
        self.assertEqual(self.rooms[0].db.adventure_session_id, newer.pk)

    def test_release_and_reuse_race_keeps_canonical_owner(self):
        """Concurrent release/reuse never overwrites a successful newer claim."""
        old = self.start()
        results = self.race([lambda: sessions.leave_session(self.players[0]),
                             lambda: sessions.start_session(self.players[1], "alpha_meadow")])
        self.assertTrue(results[0].ok)
        if not results[1].ok:
            self.start(self.players[1])
        new = AdventureSession.objects.get(instance_room=self.rooms[0], holds_instance=True)
        self.assertNotEqual(new.pk, old.pk)
        self.assertEqual(new.leader_id, self.players[1].pk)
        self.assertEqual(self.rooms[0].db.adventure_session_id, new.pk)
        self.assertFalse(sessions.expire_session(old))

    def private_battle(self):
        """A minimal live-registry fixture uses the real observation/output methods."""
        session = self.start()
        battle = BattleSession(self.players[0])
        battle.room = self.rooms[0]
        battle.encounter_metadata = {"source_type": "adventure", "adventure_session_id": session.pk}
        battle.teamA, battle.teamB = [self.players[0]], []
        battle.trainers = [self.players[0]]
        battle.observers = set()
        return battle

    def test_watch_status_and_notifications_are_private(self):
        """Direct selectors, stale observers and every central output path deny outsiders."""
        battle = self.private_battle()
        outsider = self.players[1]
        battle.add_observer(outsider)
        self.assertNotIn(outsider, battle.observers)
        REGISTRY.register(battle)
        self.addCleanup(REGISTRY.unregister, battle)
        battle.observers.add(outsider)  # stale/pre-existing registration must not leak
        self.assertEqual(REGISTRY.sessions_for(outsider), [])
        self.messages.clear()
        battle.msg("private broadcast")
        battle._msg_to(outsider, "private direct")
        self.assertFalse(any(pk == outsider.pk for pk, text in self.messages))
        ident = getattr(battle, "id", None) or getattr(battle, "uuid", None) or id(battle)
        for selector in ("@" + self.players[0].key, "#" + str(ident)):
            command = CmdEffects()
            command.caller, command.args = outsider, selector
            command.parse()
            command.func()
            self.assertEqual(self.messages[-1][1], "Battle not found. Try +status list.")
        command = CmdWatch()
        command.caller, command.args = outsider, self.players[0].key
        with patch.object(BattleSession, "ensure_for_player", return_value=battle):
            command.func()
        self.assertEqual(self.messages[-1][1], PRIVATE_MESSAGE)

    def test_staff_exception_requires_developer_permission(self):
        """Staff inspection is explicit and does not follow ordinary account identity."""
        battle = self.private_battle()
        outsider = self.players[1]
        outsider.permissions.add("Builder")
        self.assertFalse(AdventurePrivacy.battle_access(battle, outsider))
        outsider.permissions.add("Developer")
        self.assertTrue(AdventurePrivacy.battle_access(battle, outsider))
        self.assertTrue(AdventurePrivacy.room_access(self.rooms[0], outsider))

    def test_legacy_preflight_preserves_claim_and_rejects_conflict(self):
        """Read-only rollout inspection identifies exact conflicts and changes no rows."""
        session = self.start()
        before = list(AdventureSession.objects.values())
        migration = importlib.import_module("pokemon.migrations.0060_adventure_occupancy")
        report = migration.inspect_legacy_occupancy(apps, "default")
        self.assertIn(session.pk, report["held_session_ids"])
        self.assertEqual(report["errors"], [])
        self.assertEqual(list(AdventureSession.objects.values()), before)
        old = AdventureSession.objects.create(leader=self.players[0], instance_room=self.rooms[0],
                  template_key="alpha_meadow", current_node="entrance")
        report = migration.inspect_legacy_occupancy(apps, "default")
        self.assertTrue(any(str(old.pk) in error for error in report["errors"]))

    def test_pokemon_migration_state_matches_production_models(self):
        """Inspect changed app state without executing migrations or booting Evennia proxies."""
        from django.db.migrations.autodetector import MigrationAutodetector
        from django.db.migrations.loader import MigrationLoader
        from django.db.migrations.state import ProjectState

        loader = MigrationLoader(connection=None)
        changes = MigrationAutodetector(loader.project_state(), ProjectState.from_apps(apps)).changes(
            graph=loader.graph, trim_to_apps={"pokemon"})
        self.assertFalse(changes, changes)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from django.apps import apps
        from django.contrib.contenttypes.models import ContentType
        from evennia.accounts.models import AccountDB
        from evennia.commands.cmdset import CmdSet
        from evennia.commands.command import Command
        from evennia.objects.models import ObjectDB
        from evennia.utils.search import search_object

        ContentType.objects.get_for_models(*apps.get_models(), for_concrete_models=False)
        evennia.search_object = search_object
        with patch.object(evennia, "Command", Command), patch.object(evennia, "CmdSet", CmdSet):
            from commands.admin.cmd_adventureadmin import CmdAdventureAdmin
            from commands.player.cmd_effects import CmdEffects
            from commands.player.cmd_watch import CmdWatch
            from pokemon.adventures.cmdsets import AdventureMovementCmdSet
            from pokemon.adventures.commands import CmdAdventure
        from pokemon.adventures import sessions
        from pokemon.adventures.privacy import PRIVATE_MESSAGE, AdventurePrivacy
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle.registry import REGISTRY
        from pokemon.models.adventures import AdventureParticipation, AdventureSession
        from pokemon.models.trainer import Trainer

        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AdventurePrivacyCases))
        raise SystemExit(not result.wasSuccessful())

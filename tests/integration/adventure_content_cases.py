"""Rehearse Adventure installation with real Evennia objects in disposable SQL."""

from concurrent.futures import ThreadPoolExecutor
from io import StringIO
from threading import Barrier
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres


class AdventureContentCases(unittest.TestCase):
    """Exercise planning, adoption, rollback, concurrency and revision retention."""

    def setUp(self):
        """Start each case with an isolated, empty world layout."""

        AdventureSession.objects.all().delete()
        ObjectDB.objects.all().delete()
        ObjectDB.flush_instance_cache(force=True)
        self.host = create_object(ROOM, key="Town Square", nohome=True)

    def legacy_world(self):
        """Recreate the original builder batch layout."""

        hall = create_object(ROOM, key="Adventure Hall", nohome=True, aliases=["adventures"])
        hall.db.adventure_hall = True
        hall.db.desc = "Builder-authored Hall"
        instance = create_object(ROOM, key="Adventure Instance Room #1", nohome=True)
        instance.db.adventure_instance = True
        entrance = create_object(EXIT, key="adventures", location=self.host, destination=hall, nohome=True)
        create_object(EXIT, key="back", location=hall, destination=self.host, nohome=True)
        legacy_exit = create_object(EXIT, key="instance", location=hall, destination=instance, nohome=True)
        return hall, instance, entrance, legacy_exit

    def test_management_plan_and_repeat_install(self):
        """The CLI plans read-only and a repeated apply keeps every object."""

        output = StringIO()
        call_command("install_adventure_content", self.host.dbref, stdout=output)
        self.assertEqual(output.getvalue().count("Create "), 5)
        self.assertEqual(ObjectDB.objects.count(), 1)
        call_command("install_adventure_content", self.host.dbref, apply=True, stdout=StringIO())
        output = StringIO()
        call_command("install_adventure_content", self.host.dbref, apply=True, stdout=output)
        self.assertEqual(output.getvalue().count("Keep "), 5)
        self.assertEqual(ObjectDB.objects.count(), 6)

    def test_legacy_adoption_and_upgrade_keep_runs_and_unpaid_receipts(self):
        """Versions change the board without changing rooms or first clears."""

        hall, instance, entrance, legacy_exit = self.legacy_world()
        hall.permissions.add("Builder")
        instance.db.custom_stock = 3
        other = create_object(EXIT, key="side path", location=hall, destination=self.host, nohome=True)
        player = create_object("pokemon.user.User", key="Survey Owner", location=instance, nohome=True)
        paid_later = AdventureSession.objects.create(
            template_key="alpha_meadow", state="completed", leader=player, current_node="entrance",
        )
        receipt = AdventureParticipation.objects.create(
            session=paid_later, player=player, reward_item="Potion", reward_amount=1,
        )
        active = AdventureSession.objects.create(
            template_key="alpha_meadow", leader=player, current_node="old_tree",
            instance_room=instance, return_location=hall, holds_instance=True,
        )
        hall.db.adventure_instance_rooms = [instance.dbref]
        install = AdventureInstallation(self.host.pk)
        self.assertEqual(sum(action.startswith("Adopt") for action in install.install()), 4)
        self.assertEqual(install.objects["hall"].pk, hall.pk)
        self.assertEqual(install.objects["entrance"].pk, entrance.pk)
        revised = replace(ALPHA_MEADOW, version=2, name="Revised Meadow Survey")
        with patch.dict(revisions, {(revised.key, 2): revised}):
            upgrade = AdventureInstallation(self.host.pk, AdventureContent(2, {revised.key: 2}))
            self.assertEqual(sum(action.startswith("Update") for action in upgrade.install()), 5)
            self.assertEqual(board_offers(hall), [revised])
            self.assertEqual(get_session_template(active), ALPHA_MEADOW)
        receipt.refresh_from_db()
        active.refresh_from_db()
        self.assertEqual((receipt.reward_item, receipt.reward_amount, receipt.reward_claimed_at), ("Potion", 1, None))
        self.assertEqual((active.current_node, active.instance_room_id, active.return_location_id, active.holds_instance),
                         ("old_tree", instance.pk, hall.pk, True))
        self.assertEqual(hall.db.desc, "Builder-authored Hall")
        self.assertIn("builder", hall.permissions.all())
        self.assertEqual(instance.db.custom_stock, 3)
        self.assertTrue(ObjectDB.objects.filter(pk__in=[legacy_exit.pk, other.pk]).count() == 2)

    def test_duplicate_and_conflicting_paths_fail_before_mutation(self):
        """Refuse ambiguous Hall identities and a return exit to the wrong room."""

        hall, _instance, _, _ = self.legacy_world()
        duplicate = create_object(ROOM, key="Adventure Hall", nohome=True)
        count = ObjectDB.objects.count()
        with self.assertRaisesRegex(ValueError, f"ambiguous.*#{hall.pk}.*#{duplicate.pk}"):
            AdventureInstallation(self.host.pk).install()
        self.assertEqual(ObjectDB.objects.count(), count)
        duplicate.delete()
        wrong = ObjectDB.objects.get(db_key="back", db_location=hall)
        wrong.destination = hall
        with self.assertRaisesRegex(ValueError, f"return conflicts with #{wrong.pk}"):
            AdventureInstallation(self.host.pk).install()
        self.assertIsNone(hall.db.adventure_content_version)

    def test_interrupted_install_rolls_back_and_can_retry(self):
        """A failure after an object insert leaves no partial world or receipt."""

        def interrupt(*args, **kwargs):
            if kwargs.get("key") == "Adventure Mission Board":
                raise RuntimeError("injected failure")
            return create_object(*args, **kwargs)

        with patch("pokemon.adventures.content.create_object", side_effect=interrupt):
            with self.assertRaisesRegex(RuntimeError, "injected failure"):
                AdventureInstallation(self.host.pk).install()
        self.assertEqual(ObjectDB.objects.count(), 1)
        self.assertFalse(self.host.contents)
        AdventureInstallation(self.host.pk).install()
        self.assertEqual(ObjectDB.objects.count(), 6)

    def test_concurrent_install_creates_one_world(self):
        """Two independent connections replan under the same installer lock."""

        barrier = Barrier(2)

        def install():
            try:
                barrier.wait(timeout=10)
                return AdventureInstallation(self.host.pk).install()
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            first, second = [pool.submit(install) for _ in range(2)]
            counts = [sum(action.startswith("Create") for action in future.result(timeout=25))
                      for future in (first, second)]
        self.assertEqual(sorted(counts), [0, 5])
        self.assertEqual(ObjectDB.objects.count(), 6)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        from dataclasses import replace
        from django.apps import apps
        from django.contrib.contenttypes.models import ContentType
        from django.core.management import call_command
        from django.db import connections
        from evennia.objects.models import ObjectDB
        from evennia.utils.create import create_object
        from pokemon.adventures.content import AdventureContent, AdventureInstallation, EXIT, ROOM
        from pokemon.adventures.sessions import board_offers
        from pokemon.adventures.templates import ALPHA_MEADOW, _REVISIONS as revisions, get_session_template
        from pokemon.models.adventures import AdventureParticipation, AdventureSession

        ContentType.objects.get_for_models(*apps.get_models(), for_concrete_models=False)
        unittest.main(verbosity=2)

"""Isolated real-ORM lifecycle tests (the legacy suite mutates sys.modules).

Run with python tests/integration/placement_cases.py. Set PF2_TEST_POSTGRES_DSN
for real multi-connection locking and deferred PostgreSQL constraint tests.
Without it, SQLite exercises ORM transactions and row constraints; ArrayField
serialization alone is adapted to JSON and PostgreSQL-only tests are skipped.
A PostgreSQL run creates and drops ONLY a randomly named test schema.
"""

import importlib
import json
import os
import sys
import tempfile
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
from django.conf import settings

_temp = tempfile.TemporaryDirectory(prefix="pf2-placement-tests-")
_dsn = os.environ.get("PF2_TEST_POSTGRES_DSN")
_schema = "pf2_test_" + uuid.uuid4().hex
if _dsn:
    import psycopg2
    from psycopg2.extensions import parse_dsn

    params = parse_dsn(_dsn)
    admin = psycopg2.connect(_dsn)
    admin.autocommit = True
    with admin.cursor() as cursor:
        cursor.execute(f'CREATE SCHEMA "{_schema}"')
    settings.DATABASES = {"default": {
        "ENGINE": "django.db.backends.postgresql", "NAME": params.get("dbname", "postgres"),
        "USER": params.get("user", ""), "PASSWORD": params.get("password", ""),
        "HOST": params.get("host", ""), "PORT": params.get("port", ""),
        "OPTIONS": {"options": f"-c search_path={_schema}",
                    **({"sslmode": params["sslmode"]} if "sslmode" in params else {})},
    }}
else:
    settings.DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": _temp.name + "/test.sqlite3"}}
    from django.contrib.postgres.fields import ArrayField

    ArrayField.db_type = lambda self, connection: "text"
    ArrayField.cast_db_type = lambda self, connection: "text"
    ArrayField.get_placeholder = lambda self, value, compiler, connection: "%s"
    ArrayField.get_db_prep_value = lambda self, value, connection, prepared=False: json.dumps(value)
    ArrayField.from_db_value = lambda self, value, expression, connection: json.loads(value) if isinstance(value, str) else value

import django

django.setup()
from django.apps import apps
from django.db import IntegrityError, close_old_connections, connection, connections, transaction
from evennia.objects.models import ObjectDB

from pokemon.models.core import EncounterPokemon, OwnedPokemon
from pokemon.models.storage import CaptureReceipt, PokemonPlacement, StorageBox, UserStorage
from pokemon.models.trainer import Trainer
from pokemon.services.capture import finalize_wild_capture
from pokemon.services.placement import PlacementError, PlacementService
from pokemon.services.placement_audit import audit_placements_v1


def create_schema():
    """Build only the disposable test schema, never run deployment migrations."""
    with connection.schema_editor() as editor:
        for model in apps.get_models():
            editor.create_model(model)
        importlib.import_module("pokemon.migrations.0041_placement_integrity_triggers").install(apps, editor)


class PlacementCases(unittest.TestCase):
    """Exercise persisted outcomes, failures, retries, and competing writers."""

    def setUp(self):
        self.user = ObjectDB.objects.create(db_key="Trainer " + uuid.uuid4().hex)
        self.trainer = Trainer.objects.create(user=self.user, trainer_number=Trainer.objects.count() + 1)
        self.storage = UserStorage.objects.create(user=self.user)
        self.service = PlacementService(self.storage)
        self.box = StorageBox.objects.create(storage=self.storage, name="Box 1")

    def mon(self, *, party=True):
        """Create and place a real model in the same transaction."""
        with transaction.atomic():
            mon = OwnedPokemon.objects.create(trainer=self.trainer, species="Pikachu", ivs=[0]*6, evs=[0]*6)
            if party:
                self.service.to_party(mon)
            else:
                self.service.to_box(mon, self.box)
        return mon

    def assert_clean(self):
        """Audit the persisted database after every successful scenario."""
        self.assertEqual(list(audit_placements_v1(apps)), [])

    def encounter(self):
        """Create a persisted wild encounter with a stable retry identity."""
        return EncounterPokemon.objects.create(source_kind="wild", species="Pikachu", level=5,
                                               ivs=[0]*6, evs=[0]*6, current_hp=8)

    def capture(self, encounter, storage=None, trainer=None, session=None, **battle_state):
        """Use the production capture service and creation factory."""
        player = SimpleNamespace(storage=storage or self.storage, location=SimpleNamespace(key="Route 1"),
                                 ndb=SimpleNamespace(battle_instance=session))
        return finalize_wild_capture(target_poke=SimpleNamespace(model_id=f"encounter:{encounter.pk}", hp=7, **battle_state),
                                     player=player, trainer=trainer or self.trainer)

    def test_party_box_retry_and_mirrors(self):
        mon = self.mon()
        self.service.to_party(mon)
        self.service.to_box(mon, self.box)
        before = PokemonPlacement.objects.get(pokemon=mon)
        self.service.to_box(mon, self.box)
        after = PokemonPlacement.objects.get(pokemon=mon)
        self.assertEqual((before.pk, before.box_position), (after.pk, after.box_position))
        self.assertEqual(self.storage.get_party(), [])
        self.assertEqual(self.box.get_pokemon(), [mon])
        self.service.to_party(mon, 3)
        self.assertEqual(self.storage.get_stored_pokemon(), [])
        self.assertEqual(self.box.get_pokemon(), [])
        self.assert_clean()

    def test_capacity_failure_retains_box_and_full_party_retry(self):
        party = [self.mon() for _ in range(6)]
        mon = self.mon(party=False)
        self.service.to_party(party[0])  # retry succeeds even when full
        with self.assertRaisesRegex(PlacementError, "six"):
            self.service.to_party(mon)
        self.assertEqual(PokemonPlacement.objects.get(pokemon=mon).box_id, self.box.pk)
        self.assert_clean()

    def test_ownership_and_foreign_box_rejected(self):
        mon = self.mon()
        other_user = ObjectDB.objects.create(db_key="Other")
        other = UserStorage.objects.create(user=other_user)
        foreign_box = StorageBox.objects.create(storage=other, name="Other Box")
        with self.assertRaises(PlacementError):
            PlacementService(other).to_party(mon)
        with self.assertRaises(PlacementError):
            self.service.to_box(mon, foreign_box)
        with self.assertRaises(PlacementError):
            PlacementService(other).release(mon)
        self.assert_clean()

    def test_mirror_failure_rolls_back_canonical_move(self):
        mon = self.mon()
        with patch("pokemon.models.storage._sync_legacy_storage_relations", side_effect=RuntimeError("mirror failure")):
            with self.assertRaises(RuntimeError):
                self.service.to_box(mon, self.box)
        self.assertEqual(PokemonPlacement.objects.get(pokemon=mon).location_type, "party")
        self.assert_clean()

    def test_swap_atomic_and_retry(self):
        outgoing = self.mon()
        incoming = self.mon(party=False)
        self.assertEqual(self.service.swap(incoming, 1, self.box).pk, outgoing.pk)
        self.assertIsNone(self.service.swap(incoming, 1, self.box))
        self.assertEqual(PokemonPlacement.objects.get(pokemon=outgoing).box_id, self.box.pk)
        self.assert_clean()

    def test_swap_failure_rolls_back_both_members(self):
        outgoing, incoming = self.mon(), self.mon(party=False)
        with patch.object(PlacementService, "_party", side_effect=RuntimeError("party failure")):
            with self.assertRaises(RuntimeError):
                self.service.swap(incoming, 1, self.box)
        self.assertEqual(PokemonPlacement.objects.get(pokemon=outgoing).slot, 1)
        self.assertEqual(PokemonPlacement.objects.get(pokemon=incoming).box_id, self.box.pk)
        self.assert_clean()

    def test_fusion_reservation_and_full_party_return(self):
        mon = self.mon()
        self.service.reserve_for_fusion(mon)
        self.service.reserve_for_fusion(mon)
        with self.assertRaisesRegex(PlacementError, "reserved"):
            self.service.to_box(mon)
        for _ in range(6):
            self.mon()
        placement = self.service.return_from_fusion(mon, 1)
        self.assertEqual(placement.location_type, "box")
        self.assert_clean()

    def test_capture_retry_uses_receipt_after_encounter_deletion(self):
        encounter = self.encounter()
        first = self.capture(encounter)
        second = self.capture(encounter)
        self.assertEqual(first.owned_pokemon_id, second.owned_pokemon_id)
        self.assertTrue(first.should_prompt_nickname)
        self.assertFalse(second.should_prompt_nickname)
        self.assertEqual(CaptureReceipt.objects.filter(encounter_id=encounter.pk).count(), 1)
        self.assertFalse(EncounterPokemon.objects.filter(pk=encounter.pk).exists())
        self.assert_clean()

    def test_capture_preserves_live_item_and_does_not_overwrite_on_retry(self):
        """Steal/swap, consumption and absent live state survive persistence."""
        cases = [
            ({"item": SimpleNamespace(name="Leftovers")}, "Leftovers"),
            ({"item": "Sitrus Berry"}, "Sitrus Berry"),
            ({"item": None, "held_item": "Oran Berry"}, ""),
            ({"item": ""}, ""),
            ({"held_item": "Pecha Berry"}, "Pecha Berry"),
            ({"held_item": None}, ""),
            ({}, "Oran Berry"),
        ]
        for state, expected in cases:
            with self.subTest(state=state):
                encounter = self.encounter()
                EncounterPokemon.objects.filter(pk=encounter.pk).update(held_item="Oran Berry")
                result = self.capture(encounter, **state)
                receipt = CaptureReceipt.objects.get(encounter_id=encounter.pk)
                self.assertEqual(OwnedPokemon.objects.get(pk=receipt.owned_id).held_item, expected)
                retry = self.capture(encounter, item="Stale Retry Item")
                self.assertEqual(retry.owned_pokemon_id, result.owned_pokemon_id)
                self.assertEqual(OwnedPokemon.objects.get(pk=receipt.owned_id).held_item, expected)
        self.assert_clean()

    def test_capture_overflow_and_retry_after_release(self):
        for _ in range(6):
            self.mon()
        encounter = self.encounter()
        result = self.capture(encounter)
        self.assertEqual(result.placement, "storage")
        receipt = CaptureReceipt.objects.get(encounter_id=encounter.pk)
        self.service.release(receipt.pokemon)
        retry = self.capture(encounter)
        self.assertEqual(retry.owned_pokemon_id, result.owned_pokemon_id)
        self.assertFalse(OwnedPokemon.objects.filter(pk=receipt.owned_id).exists())
        self.assert_clean()

    def test_capture_rollback_and_on_commit_tracking(self):
        encounter = self.encounter()
        session = SimpleNamespace(temp_pokemon_ids=[f"encounter:{encounter.pk}"], storage=None)
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.capture(encounter, session=session)
                self.assertEqual(len(session.temp_pokemon_ids), 1)
                raise RuntimeError("outer rollback")
        self.assertFalse(CaptureReceipt.objects.filter(encounter_id=encounter.pk).exists())
        self.assertTrue(EncounterPokemon.objects.filter(pk=encounter.pk).exists())
        self.assertEqual(len(session.temp_pokemon_ids), 1)
        self.capture(encounter, session=session)
        self.assertEqual(session.temp_pokemon_ids, [])
        self.assert_clean()

    def test_capture_rejects_missing_npc_and_wrong_trainer(self):
        missing = SimpleNamespace(pk=uuid.uuid4())
        with self.assertRaises(PlacementError):
            self.capture(missing)
        encounter = self.encounter()
        EncounterPokemon.objects.filter(pk=encounter.pk).update(source_kind="npc")
        with self.assertRaises(PlacementError):
            self.capture(encounter)
        with self.assertRaises(PlacementError):
            self.capture(encounter, trainer=SimpleNamespace(user_id=-1))
        self.assert_clean()

    def test_capture_creation_failure_rolls_back(self):
        encounter = self.encounter()
        before = OwnedPokemon.objects.count()
        with patch.object(PlacementService, "place_new", side_effect=RuntimeError("placement failed")):
            with self.assertRaises(RuntimeError):
                self.capture(encounter)
        self.assertEqual(OwnedPokemon.objects.count(), before)
        self.assertTrue(EncounterPokemon.objects.filter(pk=encounter.pk).exists())
        self.assert_clean()

    def test_database_shape_and_occupancy_constraints(self):
        a, b = self.mon(party=False), self.mon(party=False)
        for changes in ({"location_type": "bad"}, {"location_type": "party", "slot": None},
                        {"box_position": 0}, {"box_position": None}):
            with self.assertRaises(IntegrityError), transaction.atomic():
                PokemonPlacement.objects.filter(pokemon=a).update(**changes)
        with self.assertRaises(IntegrityError), transaction.atomic():
            PokemonPlacement.objects.filter(pokemon=b).update(box_position=1)
        self.assert_clean()

    def test_audit_blocks_migration_and_never_repairs(self):
        mon = self.mon()
        self.storage.stored_pokemon.add(mon)  # inconsistent compatibility mirror
        problems = list(audit_placements_v1(apps))
        self.assertIn("legacy_mismatch", [p.code for p in problems])
        migration = importlib.import_module("pokemon.migrations.0040_canonical_placement")
        with self.assertRaisesRegex(RuntimeError, str(mon.pk)), transaction.atomic():
            with connection.cursor() as cursor:
                editor = SimpleNamespace(connection=connection, execute=cursor.execute)
                migration.require_valid_placements(apps, editor)
        self.assertTrue(self.storage.stored_pokemon.filter(pk=mon.pk).exists())
        self.storage.stored_pokemon.remove(mon)
        self.assert_clean()

    @unittest.skipUnless(_dsn, "requires real PostgreSQL for deferred cross-table constraints")
    def test_deferred_database_placement_and_owner_checks(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            OwnedPokemon.objects.create(trainer=self.trainer, species="Pikachu", ivs=[0]*6, evs=[0]*6)
        mon = self.mon()
        with self.assertRaises(IntegrityError), transaction.atomic():
            PokemonPlacement.objects.filter(pokemon=mon).delete()
        other_user = ObjectDB.objects.create(db_key="Foreign")
        other = UserStorage.objects.create(user=other_user)
        with self.assertRaises(IntegrityError), transaction.atomic():
            PokemonPlacement.objects.filter(pokemon=mon).update(storage=other)
        self.assert_clean()

    def run_race(self, *actions):
        """Start independent connections together and propagate unexpected failures."""
        barrier = Barrier(len(actions))
        def run(action):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    return action()
                except PlacementError as error:
                    return error
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            futures = [pool.submit(run, action) for action in actions]
            return [future.result(timeout=30) for future in futures]

    @unittest.skipUnless(_dsn and not os.environ.get("PF2_TEST_PGLITE"), "requires real PostgreSQL row locks")
    def test_concurrent_last_party_slot(self):
        for _ in range(5):
            self.mon()
        a, b = self.mon(party=False), self.mon(party=False)
        results = self.run_race(lambda: self.service.to_party(a), lambda: self.service.to_party(b))
        self.assertEqual(sum(isinstance(r, PlacementError) for r in results), 1)
        self.assertEqual(len(self.storage.get_party()), 6)
        self.assert_clean()

    @unittest.skipUnless(_dsn and not os.environ.get("PF2_TEST_PGLITE"), "requires real PostgreSQL row locks")
    def test_concurrent_conflicting_moves_and_duplicate_capture(self):
        mon = self.mon()
        self.run_race(lambda: self.service.to_box(mon, self.box), lambda: self.service.to_party(mon, 2))
        self.assertEqual(PokemonPlacement.objects.filter(pokemon=mon).count(), 1)
        encounter = self.encounter()
        results = self.run_race(lambda: self.capture(encounter), lambda: self.capture(encounter))
        self.assertEqual(results[0].owned_pokemon_id, results[1].owned_pokemon_id)
        self.assert_clean()


    @unittest.skipUnless(_dsn and not os.environ.get("PF2_TEST_PGLITE"), "requires real PostgreSQL row locks")
    def test_concurrent_capture_competing_owners(self):
        other_user = ObjectDB.objects.create(db_key="Other capturer")
        other_trainer = Trainer.objects.create(user=other_user, trainer_number=Trainer.objects.count() + 1)
        other_storage = UserStorage.objects.create(user=other_user)
        encounter = self.encounter()
        results = self.run_race(lambda: self.capture(encounter),
                                lambda: self.capture(encounter, other_storage, other_trainer))
        self.assertEqual(sum(isinstance(r, PlacementError) for r in results), 1)
        self.assertEqual(CaptureReceipt.objects.filter(encounter_id=encounter.pk).count(), 1)
        self.assert_clean()

    @unittest.skipUnless(_dsn and not os.environ.get("PF2_TEST_PGLITE"), "requires real PostgreSQL row locks")
    def test_concurrent_box_allocation_and_swaps(self):
        a, b = self.mon(), self.mon()
        self.run_race(lambda: self.service.to_box(a, self.box), lambda: self.service.to_box(b, self.box))
        positions = list(self.box.placements.values_list("box_position", flat=True))
        self.assertEqual(len(set(positions)), 2)
        self.run_race(lambda: self.service.swap(a, 1, self.box), lambda: self.service.swap(b, 1, self.box))
        self.assertEqual(self.storage.placements.filter(location_type="party", slot=1).count(), 1)
        self.assert_clean()


if __name__ == "__main__":
    try:
        create_schema()
        unittest.main(verbosity=2)
    finally:
        connections.close_all()
        if _dsn:
            with admin.cursor() as cursor:
                cursor.execute(f'DROP SCHEMA "{_schema}" CASCADE')
            admin.close()
        _temp.cleanup()

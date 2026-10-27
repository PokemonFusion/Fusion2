"""Native-pair integrity with real production models in disposable PostgreSQL.

The initial schema cases prepare pairs as separate internal setup, not ordinary
player acquisition/command acceptance. No game database or migration is selected.
"""

import importlib
import sys
import unittest
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from isolated_postgres import IsolatedPostgres

database = IsolatedPostgres()
database.__enter__()

from django.apps import apps
from django.db import IntegrityError, connection, transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from evennia.objects.models import ObjectDB

from pokemon.models.core import OwnedPokemon
from pokemon.models.moves import ActiveMoveslot, Move, MovePPBoost, Moveset, MovesetSlot, PokemonLearnedMove
from pokemon.models.necrozma import NecrozmaCombination, NecrozmaOperation, NecrozmaResource
from pokemon.models.ownership import PokemonReservation
from pokemon.models.storage import PokemonPlacement, StorageBox, UserStorage
from pokemon.models.trainer import Trainer
from pokemon.services.necrozma_audit import audit_necrozma_v1, require_necrozma_baseline
from pokemon.services.placement import PlacementService
from pokemon.services.placement_audit import audit_placements_v3


class NecrozmaSchemaCases(unittest.TestCase):
    """Assert final SQL and invalid bulk-write commits rather than model save hooks."""

    def setUp(self):
        """Give every case its own character and two genuine base source rows."""
        self.owner = ObjectDB.objects.create(db_key="Native pair QA " + uuid4().hex,
            db_typeclass_path="pokemon.user.User")
        self.trainer, _ = Trainer.objects.get_or_create(user=self.owner,
            defaults={"trainer_number": Trainer.objects.count() + 1})
        self.storage, _ = UserStorage.objects.get_or_create(user=self.owner)
        self.host = self.mon("Necrozma", "Prism Armor", 3)
        self.companion = self.mon("Solgaleo", "Full Metal Body", 5)
        self.moveset = Moveset.objects.create(pokemon=self.host, index=0)
        OwnedPokemon.objects.filter(pk=self.host.pk).update(active_moveset=self.moveset)
        self.ordinary, _ = Move.objects.get_or_create(name="Tackle")
        PokemonLearnedMove.objects.create(pokemon=self.host, move=self.ordinary)
        MovesetSlot.objects.create(moveset=self.moveset, move=self.ordinary, slot=2)
        ActiveMoveslot.objects.create(pokemon=self.host, move=self.ordinary, slot=2, current_pp=3)

    def mon(self, species, ability, slot):
        """Atomically place a base source; never fabricate native pair provenance."""
        with transaction.atomic():
            pokemon = OwnedPokemon.objects.create(trainer=self.trainer, species=species, ability=ability,
                level=50, ivs=[1, 2, 3, 4, 5, 6], evs=[0] * 6, current_hp=10, status="psn")
            PlacementService(self.storage).to_party(pokemon, slot)
        return pokemon

    def pair(self, *, dawn=False):
        """Internal foundation setup; public service/command tests are separate."""
        with transaction.atomic():
            if dawn:
                OwnedPokemon.objects.filter(pk=self.companion.pk).update(species="Lunala", ability="Shadow Shield")
            source = "Moongeist Beam" if dawn else "Sunsteel Strike"
            move, _ = Move.objects.get_or_create(name=source)
            resource = NecrozmaResource.objects.create(host=self.host, source=source, current_pp=5)
            pair = NecrozmaCombination(storage=self.storage, host=self.host,
                companion=self.companion, target_species="Necrozma-Dawn-Wings" if dawn else "Necrozma-Dusk-Mane",
                resource=resource, moveset=self.moveset, move_slot=2, displaced_move=self.ordinary,
                displaced_pp=3, return_type="party", return_slot=5)
            OwnedPokemon.objects.filter(pk=self.host.pk).update(species=pair.target_species)
            PokemonLearnedMove.objects.create(pokemon=self.host, move=move)
            ActiveMoveslot.objects.filter(pokemon=self.host, slot=2).update(move=move, current_pp=5)
            MovesetSlot.objects.filter(moveset=self.moveset, slot=2).update(move=move)
            placement = PokemonPlacement.objects.get(pokemon=self.companion)
            placement.location_type, placement.slot, placement.combination = "combined", None, pair
            PokemonPlacement.objects.filter(pk=placement.pk).update(location_type="combined", slot=None, combination_id=pair.pk)
            from pokemon.models.storage import _sync_legacy_storage_relations

            _sync_legacy_storage_relations(self.storage, self.companion)
            pair.save()
            NecrozmaOperation.objects.create(storage=self.storage, action="combine", state="completed",
                terms={"host": str(self.host.pk), "companion": str(self.companion.pk), "source": source,
                       "lifecycle": str(pair.pk), "version": 1, "slot": 2},
                expires_at=timezone.now() + timedelta(minutes=5), completed_at=timezone.now(),
                result={"lifecycle": str(pair.pk)})
        return pair

    def separate_setup(self, pair):
        """Undo the internal setup atomically without deleting either source."""
        with transaction.atomic():
            placement = PokemonPlacement.objects.get(pokemon=self.companion)
            placement.location_type, placement.slot, placement.combination = "party", 5, None
            placement.save()
            NecrozmaCombination.objects.filter(pk=pair.pk).delete()
            ActiveMoveslot.objects.filter(pokemon=self.host, slot=2).update(move=self.ordinary, current_pp=3)
            MovesetSlot.objects.filter(moveset=self.moveset, slot=2).update(move=self.ordinary)
            PokemonLearnedMove.objects.filter(pokemon=self.host, move__name=pair.resource.source).delete()
            OwnedPokemon.objects.filter(pk=self.host.pk).update(species="Necrozma")

    def tearDown(self):
        """Every legal outcome must retain canonical custody and mirrors."""
        self.assertEqual(list(audit_placements_v3(apps)), [])

    def test_both_forms_have_two_identities_and_reserved_companion(self):
        pair = self.pair(dawn=True)
        self.assertEqual(self.storage.get_party_slots()[2].pk, self.host.pk)
        self.assertIsNone(self.storage.get_party_slots()[4])
        self.assertEqual(OwnedPokemon.objects.filter(pk__in=(self.host.pk, self.companion.pk)).count(), 2)
        self.assertFalse(self.companion.active_slots.exists())
        self.assertFalse(self.companion.stored_users.exists())
        self.assertFalse(self.companion.boxes.exists())
        self.assertEqual(list(audit_necrozma_v1(apps)), [])
        self.assertEqual(pair.resource.current_pp, 5)

    def test_foreign_owner_species_ability_and_egg_bulk_changes_rejected(self):
        pair = self.pair()
        updates = ((self.host, {"species": "Necrozma"}), (self.host, {"ability": "Levitate"}),
                   (self.companion, {"species": "Lunala"}), (self.companion, {"is_egg": True}))
        for pokemon, update in updates:
            with self.subTest(update=update), self.assertRaises(IntegrityError), transaction.atomic():
                OwnedPokemon.objects.filter(pk=pokemon.pk).update(**update)
        with self.assertRaises(IntegrityError), transaction.atomic():
            NecrozmaCombination.objects.filter(pk=pair.pk).update(target_species="Necrozma-Dawn-Wings")

    def test_cross_role_reuse_and_missing_reciprocal_placement_rejected(self):
        pair = self.pair()
        with self.assertRaises(IntegrityError), transaction.atomic():
            NecrozmaCombination.objects.filter(pk=pair.pk).update(companion_id=self.host.pk)
        with self.assertRaises(IntegrityError), transaction.atomic():
            PokemonPlacement.objects.filter(pokemon=self.companion).update(
                location_type="party", slot=5, combination=None)
        with self.assertRaises(IntegrityError), transaction.atomic():
            PokemonPlacement.objects.filter(pokemon=self.host).delete()

    def test_slot_set_learned_resource_and_boost_corruption_rejected(self):
        pair = self.pair()
        mutations = (
            lambda: NecrozmaResource.objects.filter(pk=pair.resource_id).update(current_pp=4),
            lambda: ActiveMoveslot.objects.filter(pokemon=self.host, slot=2).update(move=self.ordinary),
            lambda: MovesetSlot.objects.filter(moveset=self.moveset, slot=2).delete(),
            lambda: PokemonLearnedMove.objects.filter(pokemon=self.host, move__name="Sunsteel Strike").delete(),
            lambda: OwnedPokemon.objects.filter(pk=self.host.pk).update(active_moveset=None),
            lambda: NecrozmaResource.objects.filter(pk=pair.resource_id).update(current_pp=8),
            lambda: MovePPBoost.objects.create(pokemon=self.host, move=pair.resource.host.active_moves[0], bonus_pp=4),
        )
        for mutation in mutations:
            with self.assertRaises(IntegrityError), transaction.atomic():
                mutation()

    def test_resource_and_active_pp_commit_together_including_zero(self):
        pair = self.pair()
        with transaction.atomic():
            ActiveMoveslot.objects.filter(pokemon=self.host, slot=2).update(current_pp=0)
            NecrozmaResource.objects.filter(pk=pair.resource_id).update(current_pp=0)
        self.assertEqual(NecrozmaResource.objects.get(pk=pair.resource_id).current_pp, 0)
        self.separate_setup(pair)
        self.assertEqual(NecrozmaResource.objects.get(pk=pair.resource_id).current_pp, 0)

    def test_canonical_bulk_pp_write_mirrors_source_history_in_same_transaction(self):
        pair = self.pair()
        ActiveMoveslot.objects.filter(pokemon=self.host, slot=2).update(current_pp=2)
        self.assertEqual(NecrozmaResource.objects.get(pk=pair.resource_id).current_pp, 2)
        with self.assertRaisesRegex(RuntimeError, "outer"), transaction.atomic():
            ActiveMoveslot.objects.filter(pokemon=self.host, slot=2).update(current_pp=0)
            self.assertEqual(NecrozmaResource.objects.get(pk=pair.resource_id).current_pp, 0)
            raise RuntimeError("outer")
        self.assertEqual(NecrozmaResource.objects.get(pk=pair.resource_id).current_pp, 2)
        self.separate_setup(pair)
        self.assertEqual(NecrozmaResource.objects.get(pk=pair.resource_id).current_pp, 2)

    def test_combined_shape_and_legacy_mirror_bypass_rejected(self):
        self.pair()
        with self.assertRaises(IntegrityError), transaction.atomic():
            PokemonPlacement.objects.filter(pokemon=self.companion).update(slot=1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.storage.stored_pokemon.add(self.companion)
        with self.assertRaises(IntegrityError), transaction.atomic():
            PokemonReservation.objects.create(pokemon=self.companion, storage=self.storage,
                kind="market", token=uuid4())

    def test_native_host_mirrors_cannot_hide_duplicate_or_missing_membership(self):
        from pokemon.models.storage import ActivePokemonSlot

        self.pair()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.storage.stored_pokemon.add(self.host)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ActivePokemonSlot.objects.filter(pokemon=self.host).delete()

    def test_unpaired_direct_fused_grant_and_unbound_base_sources_rejected(self):
        for name in ("Necrozma-Dusk-Mane", "necrozmaduskmane", "Necrozma Dawn Wings"):
            with self.assertRaises(IntegrityError), transaction.atomic():
                OwnedPokemon.objects.filter(pk=self.host.pk).update(species=name)
        for name in ("Sunsteel Strike", "moongeistbeam"):
            with self.assertRaises(IntegrityError), transaction.atomic():
                move, _ = Move.objects.get_or_create(name=name)
                PokemonLearnedMove.objects.create(pokemon=self.host, move=move)

    def test_storage_and_trainer_reassignment_cannot_steal_either_source(self):
        self.pair()
        foreign = ObjectDB.objects.create(db_key="Foreign QA " + uuid4().hex)
        trainer = Trainer.objects.create(user=foreign, trainer_number=Trainer.objects.count() + 1)
        for pokemon in (self.host, self.companion):
            with self.assertRaises(IntegrityError), transaction.atomic():
                OwnedPokemon.objects.filter(pk=pokemon.pk).update(trainer=trainer)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Trainer.objects.filter(pk=self.trainer.pk).update(user=foreign)
        with self.assertRaises(IntegrityError), transaction.atomic():
            UserStorage.objects.filter(pk=self.storage.pk).update(user=foreign)

    def test_resource_requires_own_host_correct_move_and_actual_capacity(self):
        pair = self.pair()
        for update in ({"host": self.companion}, {"source": "Moongeist Beam"}, {"policy_version": 2}):
            with self.assertRaises(IntegrityError), transaction.atomic():
                NecrozmaResource.objects.filter(pk=pair.resource_id).update(**update)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Move.objects.filter(name="Sunsteel Strike").update(name="Sunsteel alias")
        with transaction.atomic():
            MovePPBoost.objects.create(pokemon=self.host, move=Move.objects.get(name="Sunsteel Strike"), bonus_pp=3)
            ActiveMoveslot.objects.filter(pokemon=self.host, slot=2).update(current_pp=8)
            NecrozmaResource.objects.filter(pk=pair.resource_id).update(current_pp=8)
        self.assertEqual(NecrozmaResource.objects.get(pk=pair.resource_id).current_pp, 8)
        with self.assertRaises(IntegrityError), transaction.atomic():
            MovePPBoost.objects.filter(pokemon=self.host).update(bonus_pp=0)

    def test_live_foreign_keys_protect_sources_but_history_allows_later_release(self):
        pair = self.pair()
        for pokemon in (self.host, self.companion):
            with self.assertRaises(ProtectedError):
                pokemon.delete()
        operation = NecrozmaOperation.objects.create(storage=self.storage, action="combine",
            terms={"host": str(self.host.pk), "companion": str(self.companion.pk)},
            expires_at=timezone.now() + timedelta(minutes=5), state="completed",
            completed_at=timezone.now(), result={"lifecycle": str(pair.pk)})
        self.separate_setup(pair)
        PlacementService(self.storage).release(self.host)
        self.assertTrue(NecrozmaOperation.objects.filter(pk=operation.pk).exists())
        self.assertFalse(NecrozmaResource.objects.filter(host_id=self.host.pk).exists())

    def test_parent_rollback_leaves_base_sources_and_no_pair_or_resource(self):
        with self.assertRaisesRegex(RuntimeError, "outer"), transaction.atomic():
            self.pair()
            raise RuntimeError("outer")
        self.assertEqual(OwnedPokemon.objects.values_list("species", flat=True).get(pk=self.host.pk), "Necrozma")
        self.assertFalse(NecrozmaCombination.objects.filter(host=self.host).exists())
        self.assertFalse(NecrozmaResource.objects.filter(host=self.host).exists())
        self.assertEqual(PokemonPlacement.objects.get(pokemon=self.companion).slot, 5)

    def test_request_terms_and_terminal_receipts_are_sealed(self):
        operation = NecrozmaOperation.objects.create(storage=self.storage, action="combine", terms={"host": str(self.host.pk)},
            expires_at=timezone.now() + timedelta(minutes=5))
        for update in ({"terms": {}}, {"action": "separate"}, {"expires_at": timezone.now()}):
            with self.assertRaises(IntegrityError), transaction.atomic():
                NecrozmaOperation.objects.filter(pk=operation.pk).update(**update)
        NecrozmaOperation.objects.filter(pk=operation.pk).update(state="completed", completed_at=timezone.now(), result={"host":str(self.host.pk)})
        with self.assertRaises(IntegrityError), transaction.atomic():
            NecrozmaOperation.objects.filter(pk=operation.pk).update(result={"tampered": True})

    def test_baseline_preflight_is_read_only_and_refuses_ambiguous_legacy(self):
        # Existing legal pairs are deliberately invalid *baseline* data: do not
        # use this pre-upgrade audit to inspect an already upgraded live schema.
        pair = self.pair()
        before = list(OwnedPokemon.objects.filter(pk__in=(self.host.pk, self.companion.pk)).values())
        with connection.schema_editor() as editor:
            with self.assertRaisesRegex(RuntimeError, "baseline audit"):
                require_necrozma_baseline(apps, editor)
        self.assertEqual(before, list(OwnedPokemon.objects.filter(pk__in=(self.host.pk, self.companion.pk)).values()))
        self.assertTrue(NecrozmaCombination.objects.filter(pk=pair.pk).exists())


if __name__ == "__main__":
    try:
        database.create_model_tables()
        with connection.schema_editor() as editor:
            importlib.import_module("pokemon.migrations.0041_placement_integrity_triggers").install(apps, editor)
            importlib.import_module("pokemon.migrations.0058_necrozma_integrity").install(apps, editor)
        unittest.main(verbosity=2)
    finally:
        database.close()

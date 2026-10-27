"""Atomic native-pair service, reservations and competing writers in private SQL."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
from threading import Barrier
import unittest
from unittest.mock import patch
from uuid import uuid4

import necrozma_cases as core
from django.apps import apps
from django.db import IntegrityError, connection, connections, transaction
from django.utils import timezone
from evennia.objects.models import ObjectDB

from pokemon.models.core import OwnedPokemon
from pokemon.models.moves import ActiveMoveslot, MovesetSlot
from pokemon.models.necrozma import NecrozmaCombination, NecrozmaOperation, NecrozmaResource
from pokemon.models.storage import PokemonPlacement, StorageBox, UserStorage
from pokemon.services.evolution import EvolutionError, EvolutionService
from pokemon.services.field_abilities import FieldAbilityUse
from pokemon.services.field_items import FieldMedicineError, FieldMedicineUse
from pokemon.services.necrozma import NecrozmaService, json_state
from pokemon.services.necrozma_guards import NecrozmaError, assert_operation
from pokemon.services.ownership import PokemonReservations, claim_battle, fresh_owned
from pokemon.services.placement import PlacementError, PlacementService
from pokemon.services.placement_audit import audit_placements_v3


class NecrozmaLifecycleCases(unittest.TestCase):
    """Keep internal setup/fault writes distinct from ordinary player input."""

    mon = core.NecrozmaSchemaCases.mon

    def setUp(self):
        """Use gapped canonical slots and an actually persisted Center location."""
        core.NecrozmaSchemaCases.setUp(self)
        self.center = ObjectDB.objects.create(db_key="Native QA Center " + uuid4().hex)
        self.center.attributes.add("is_pokemon_center", True)
        ObjectDB.objects.filter(pk=self.owner.pk).update(db_location=self.center)
        self.service = NecrozmaService(self.owner)

    def tearDown(self):
        """SQL custody and source bindings must remain valid after every outcome."""
        self.assertEqual(list(audit_placements_v3(apps)), [])

    def combine(self, *, slot=2):
        """Run the production review and commit without replacing its effects."""
        operation = self.service.prepare("combine", str(self.host.pk), str(self.companion.pk), slot)
        result, applied = self.service.commit(operation.pk)
        self.assertTrue(applied)
        return operation, result

    def separate(self):
        operation = self.service.prepare("separate", str(self.host.pk))
        result, applied = self.service.commit(operation.pk)
        self.assertTrue(applied)
        return operation, result

    def snapshot(self):
        """Include fresh persisted sources, placements, slots, resources and receipts."""
        return json_state({
            "owned": list(OwnedPokemon.objects.filter(trainer=self.trainer).order_by("pk").values()),
            "placement": list(PokemonPlacement.objects.filter(storage=self.storage).order_by("pokemon_id").values()),
            "active": list(ActiveMoveslot.objects.filter(pokemon__trainer=self.trainer).order_by("pokemon_id", "slot").values()),
            "saved": list(MovesetSlot.objects.filter(moveset__pokemon__trainer=self.trainer).order_by("pk").values()),
            "resource": list(NecrozmaResource.objects.filter(host__trainer=self.trainer).order_by("pk").values()),
            "pairs": list(NecrozmaCombination.objects.filter(storage=self.storage).values()),
            "operations": list(NecrozmaOperation.objects.filter(storage=self.storage).order_by("pk").values()),
        })

    def test_dusk_preserves_two_rows_genetics_status_and_displaced_pp(self):
        before = self.snapshot()
        operation, result = self.combine()
        self.assertEqual(result["target"], "Necrozma-Dusk-Mane")
        after = self.snapshot()
        expected = deepcopy(before["owned"])
        next(row for row in expected if row["unique_id"] == str(self.host.pk))["species"] = "Necrozma-Dusk-Mane"
        self.assertEqual(after["owned"], expected)
        self.assertEqual(self.service.commit(operation.pk), (result, False))
        _, separated = self.separate()
        self.assertEqual(self.snapshot()["owned"], before["owned"])
        self.assertEqual(ActiveMoveslot.objects.get(pokemon=self.host, slot=2).current_pp, 3)
        self.assertEqual(separated["return"]["slot"], 5)
        self.assertEqual(OwnedPokemon.objects.filter(trainer=self.trainer).count(), 2)

    def test_new_native_sources_have_coherent_species_growth_before_item_use(self):
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.models.stats import exp_for_level, level_for_exp
        from pokemon.dex import POKEDEX
        from pokemon.names import resolve_dex_entry

        for species in ("Necrozma", "Solgaleo", "Lunala"):
            entry = resolve_dex_entry(POKEDEX, species)
            pokemon = create_owned_pokemon(species, self.trainer, 50,
                ability=entry.raw["abilities"]["0"], nature="Hardy", ivs=[0] * 6, evs=[0] * 6)
            growth = entry.raw.get("growthRate", "medium_fast")
            row = OwnedPokemon.objects.filter(pk=pokemon.pk).values().get()
            self.assertEqual(row["total_exp"], exp_for_level(50, growth))
            self.assertEqual(level_for_exp(row["total_exp"], growth), row["level"])
            self.assertEqual(fresh_owned(pokemon.pk).computed_level, 50)

    def test_dawn_boxed_sources_keep_host_box_and_prefer_companions_box(self):
        OwnedPokemon.objects.filter(pk=self.companion.pk).update(species="Lunala", ability="Shadow Shield")
        service = PlacementService(self.storage)
        host_box, companion_box = [StorageBox.objects.create(storage=self.storage, name=name) for name in ("Host", "Partner")]
        service.to_box(self.host, host_box)
        service.to_box(self.companion, companion_box)
        old = PokemonPlacement.objects.get(pokemon=self.host)
        self.combine()
        self.assertEqual(OwnedPokemon.objects.values_list("species", flat=True).get(pk=self.host.pk), "Necrozma-Dawn-Wings")
        now = PokemonPlacement.objects.get(pokemon=self.host)
        self.assertEqual((old.pk, old.box_id, old.box_position), (now.pk, now.box_id, now.box_position))
        self.separate()
        self.assertEqual(PokemonPlacement.objects.get(pokemon=self.companion).box_id, companion_box.pk)

    def test_full_party_and_deleted_box_hints_return_without_eviction(self):
        self.combine()
        for slot in (1, 2, 4, 5, 6):
            self.mon("Eevee", "Run Away", slot)
        old_party = list(PokemonPlacement.objects.filter(storage=self.storage, location_type="party").order_by("slot").values_list("pokemon_id", "slot"))
        _, result = self.separate()
        self.assertEqual(result["return"]["location"], "box")
        self.assertEqual(old_party, list(PokemonPlacement.objects.filter(storage=self.storage, location_type="party").order_by("slot").values_list("pokemon_id", "slot")))
        self.combine()
        box = StorageBox.objects.filter(storage=self.storage).first()
        box.delete()  # it is now an empty historical hint, not live companion custody
        self.separate()
        self.assertEqual(PokemonPlacement.objects.get(pokemon=self.companion).location_type, "box")

    def test_fainted_statused_host_can_separate_and_never_replays_old_health(self):
        self.combine()
        OwnedPokemon.objects.filter(pk=self.host.pk).update(current_hp=0, status="slp", sleep_turns=3, friendship=100)
        self.separate()
        row = OwnedPokemon.objects.filter(pk=self.host.pk).values().get()
        self.assertEqual((row["current_hp"], row["status"], row["sleep_turns"], row["friendship"]), (0, "slp", 3, 100))

    def test_empty_slot_source_removed_without_compacting_other_slots(self):
        self.combine(slot=4)
        ActiveMoveslot.objects.filter(pokemon=self.host, slot=2).update(current_pp=1)
        self.separate()
        self.assertEqual(list(ActiveMoveslot.objects.filter(pokemon=self.host).values_list("slot", "move__name", "current_pp")), [(2, "Tackle", 1)])
        self.assertFalse(MovesetSlot.objects.filter(moveset=self.moveset, slot=4).exists())

    def test_zero_pp_survives_separation_and_partner_changes(self):
        self.combine()
        with transaction.atomic():
            ActiveMoveslot.objects.filter(pokemon=self.host, slot=2).update(current_pp=0)
            NecrozmaResource.objects.filter(host=self.host, source="Sunsteel Strike").update(current_pp=0)
        self.separate()
        self.combine()
        self.assertEqual(ActiveMoveslot.objects.get(pokemon=self.host, slot=2).current_pp, 0)
        self.separate()
        other = self.mon("Lunala", "Shadow Shield", 6)
        op = self.service.prepare("combine", "3", "6", 4)
        self.service.commit(op.pk)
        self.assertEqual(ActiveMoveslot.objects.get(pokemon=self.host, slot=4).current_pp, 5)
        self.separate()
        self.assertEqual(OwnedPokemon.objects.filter(pk=other.pk).values_list("species", flat=True).get(), "Lunala")
        self.combine()
        self.assertEqual(ActiveMoveslot.objects.get(pokemon=self.host, slot=2).current_pp, 0)

    def test_missing_previous_resource_fails_closed_instead_of_refilling(self):
        self.combine()
        self.separate()
        original = NecrozmaResource.objects.filter(host=self.host).values().get()
        NecrozmaResource.objects.filter(host=self.host).delete()  # deliberate disposable corruption
        before = self.snapshot()
        with self.assertRaisesRegex(NecrozmaError, "history"):
            self.service.prepare("combine", "3", "5", 2)
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(any(problem.code == "necrozma_missing_history_resource" for problem in audit_placements_v3(apps)))
        NecrozmaResource.objects.create(**original)  # restore only deliberately corrupted QA history

    def test_stale_review_cancel_expiry_and_location_change_do_not_mutate_sources(self):
        operation = self.service.prepare("combine", "3", "5", 2)
        OwnedPokemon.objects.filter(pk=self.host.pk).update(nickname="Current name")
        before = self.snapshot()
        with self.assertRaisesRegex(NecrozmaError, "stale"):
            self.service.commit(operation.pk)
        self.assertEqual(before, self.snapshot())
        self.service.cancel(operation.pk)
        with self.assertRaisesRegex(NecrozmaError, "pending"):
            self.service.commit(operation.pk)
        expired = self.service.prepare("combine", "3", "5", 2)
        with patch("pokemon.services.necrozma.timezone.now", return_value=expired.expires_at + timedelta(seconds=1)):
            result, applied = self.service.commit(expired.pk)
        self.assertFalse(applied)
        self.assertIn("expired", result["error"])
        self.assertEqual(NecrozmaOperation.objects.get(pk=expired.pk).state, "expired")
        operation = self.service.prepare("combine", "3", "5", 2)
        ObjectDB.objects.filter(pk=self.owner.pk).update(db_location=None)
        before = self.snapshot()
        with self.assertRaisesRegex(NecrozmaError, "Center"):
            self.service.commit(operation.pk)
        self.assertEqual(before, self.snapshot())

    def test_old_separation_request_cannot_undo_new_cycle_or_resurrect_release(self):
        self.combine()
        old = self.service.prepare("separate", "3")
        _, result = self.separate()
        self.combine()
        before = self.snapshot()
        with self.assertRaisesRegex(NecrozmaError, "lifecycle"):
            self.service.commit(old.pk)
        self.assertEqual(before, self.snapshot())
        self.separate()
        PlacementService(self.storage).release(self.host)
        # Completed history stays readable after release, without creating rows.
        last = NecrozmaOperation.objects.filter(storage=self.storage, action="separate", state="completed").latest("completed_at")
        self.assertEqual(self.service.commit(last.pk), (last.result, False))
        self.assertFalse(OwnedPokemon.objects.filter(pk=self.host.pk).exists())

    def test_each_combine_write_and_parent_rollback_retains_current_sources(self):
        stages = []
        operation = self.service.prepare("combine", "3", "5", 2)
        with patch.object(self.service, "_wrote", side_effect=stages.append):
            self.service.commit(operation.pk)
        self.separate()
        for stage in stages:
            operation = self.service.prepare("combine", "3", "5", 2)
            before = self.snapshot()
            def fail(current, selected=stage):
                if current == selected:
                    raise RuntimeError("Injected " + selected)
            with self.subTest(stage=stage), patch.object(self.service, "_wrote", side_effect=fail):
                with self.assertRaisesRegex(RuntimeError, "Injected"):
                    self.service.commit(operation.pk)
            self.assertEqual(before, self.snapshot())
            self.assertEqual(fresh_owned(self.host.pk).species, "Necrozma")
        operation = self.service.prepare("combine", "3", "5", 2)
        before = self.snapshot()
        with self.assertRaisesRegex(RuntimeError, "outer"), transaction.atomic():
            self.service.commit(operation.pk)
            raise RuntimeError("outer")
        self.assertEqual(self.snapshot(), before)

    def test_each_separate_write_and_no_destination_failure_retains_valid_pair(self):
        self.combine()
        stages = []
        operation = self.service.prepare("separate", "3")
        with patch.object(self.service, "_wrote", side_effect=stages.append):
            self.service.commit(operation.pk)
        self.combine()
        for stage in stages:
            operation = self.service.prepare("separate", "3")
            before = self.snapshot()
            def fail(current, selected=stage):
                if current == selected:
                    raise RuntimeError("Injected " + selected)
            with self.subTest(stage=stage), patch.object(self.service, "_wrote", side_effect=fail):
                with self.assertRaisesRegex(RuntimeError, "Injected"):
                    self.service.commit(operation.pk)
            self.assertEqual(before, self.snapshot())
            self.assertEqual(fresh_owned(self.host.pk).species, "Necrozma-Dusk-Mane")
        operation = self.service.prepare("separate", "3")
        before = self.snapshot()
        with patch.object(PlacementService, "_party", side_effect=PlacementError("No legal destination")):
            with self.assertRaises(PlacementError):
                self.service.commit(operation.pk)
        self.assertEqual(self.snapshot(), before)

    def test_companion_and_unreviewed_host_operations_reject_before_writes(self):
        self.combine()
        placement = PlacementService(self.storage)
        for mon in (self.host, self.companion):
            for action in (lambda: placement.to_box(mon), lambda: placement.release(mon),
                           lambda: placement.reserve_for_fusion(mon),
                           lambda: PokemonReservations(self.owner).claim("market", [mon.pk], uuid4())):
                with self.assertRaises(PlacementError):
                    action()
        self.assertEqual(assert_operation(self.companion.pk, "inspect")["host_id"], self.host.pk)
        self.trainer.add_item("Ability Patch", 1)
        with self.assertRaises(FieldMedicineError):
            FieldAbilityUse(self.owner).use("Ability Patch", "3")
        self.assertEqual(self.trainer.get_item_quantity("Ability Patch"), 1)
        with self.assertRaises(EvolutionError):
            EvolutionService(self.owner).evolve(self.host)
        for update in ({"current_hp": 1}, {"held_item": "Oran Berry"}, {"friendship": 200}):
            with self.assertRaises(IntegrityError), transaction.atomic():
                OwnedPokemon.objects.filter(pk=self.companion.pk).update(**update)

    def test_host_medicine_held_items_and_battle_admission_use_shared_boundary(self):
        self.combine()
        before = OwnedPokemon.objects.filter(pk=self.companion.pk).values().get()
        self.trainer.add_item("Potion", 1)
        self.assertTrue(FieldMedicineUse(self.owner).use("Potion", "3"))
        self.trainer.add_item("Leftovers", 1)
        self.assertIn("holding", EvolutionService(self.owner).hold(3, "Leftovers"))
        battle_id = uuid4()
        claim_battle(self.owner, battle_id)
        with self.assertRaises(PlacementError):
            self.service.prepare("separate", "3")
        self.owner.attributes.remove("battle_lock")
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.companion.pk).values().get(), before)
        self.separate()

    @staticmethod
    def race(*actions):
        """Use independent database connections and a common starting barrier."""
        barrier = Barrier(len(actions))
        def run(action):
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                try:
                    return action()
                except PlacementError as error:
                    return error
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(actions)) as executor:
            return list(executor.map(run, actions))

    def test_independent_combine_and_separate_contention_has_one_outcome(self):
        a = self.service.prepare("combine", "3", "5", 2)
        b = self.service.prepare("combine", "3", "5", 2)
        outcomes = self.race(lambda: self.service.commit(a.pk), lambda: self.service.commit(b.pk))
        self.assertEqual(sum(isinstance(value, PlacementError) for value in outcomes), 1)
        self.assertEqual(NecrozmaCombination.objects.filter(storage=self.storage).count(), 1)
        a = self.service.prepare("separate", "3")
        b = self.service.prepare("separate", "3")
        outcomes = self.race(lambda: self.service.commit(a.pk), lambda: self.service.commit(b.pk))
        self.assertEqual(sum(isinstance(value, PlacementError) for value in outcomes), 1)
        self.assertFalse(NecrozmaCombination.objects.filter(storage=self.storage).exists())

    def test_battle_claim_serializes_against_combine_without_deadlock(self):
        operation = self.service.prepare("combine", "3", "5", 2)
        battle_id = uuid4()
        outcomes = self.race(lambda: self.service.commit(operation.pk), lambda: claim_battle(self.owner, battle_id))
        self.assertNotIn("deadlock", str(outcomes).lower())
        self.assertEqual(sum(isinstance(value, PlacementError) for value in outcomes),
                         0 if NecrozmaCombination.objects.filter(storage=self.storage).exists() else 1)
        self.owner.attributes.remove("battle_lock")

    def test_fusion_and_transfer_reservation_races_keep_one_claim(self):
        """Independent existing claim writers cannot reserve a linked companion."""
        for claim in ("fusion", "market"):
            operation = self.service.prepare("combine", "3", "5", 2)
            token = uuid4()
            alternative = (lambda: PlacementService(self.storage).reserve_for_fusion(self.companion)) if claim == "fusion" else (
                lambda: PokemonReservations(self.owner).claim("market", [self.companion.pk], token))
            outcomes = self.race(lambda: self.service.commit(operation.pk), alternative)
            self.assertEqual(sum(isinstance(value, PlacementError) for value in outcomes), 1)
            self.assertNotIn("deadlock", str(outcomes).lower())
            self.assertEqual(OwnedPokemon.objects.filter(trainer=self.trainer).count(), 2)
            if NecrozmaCombination.objects.filter(storage=self.storage).exists():
                self.separate()
            elif claim == "fusion":
                PlacementService(self.storage).return_from_fusion(self.companion, preferred_slot=5)
            else:
                PokemonReservations(self.owner).release("market", token)
            self.assertEqual(PokemonPlacement.objects.get(pokemon=self.companion).location_type, "party")

    def test_foreign_same_account_sources_names_gaps_and_wrong_forms_reject(self):
        from evennia.accounts.models import AccountDB
        from pokemon.models.trainer import Trainer

        account = AccountDB.objects.create(username="native-alt-" + uuid4().hex)
        ObjectDB.objects.filter(pk=self.owner.pk).update(db_account=account)
        alt = ObjectDB.objects.create(db_key="Same-account alt", db_account=account, db_typeclass_path="pokemon.user.User")
        trainer, _ = Trainer.objects.get_or_create(user=alt, defaults={"trainer_number": Trainer.objects.count() + 1})
        storage, _ = UserStorage.objects.get_or_create(user=alt)
        with transaction.atomic():
            foreign = OwnedPokemon.objects.create(trainer=trainer, species="Solgaleo", ability="Full Metal Body",
                ivs=[0] * 6, evs=[0] * 6, current_hp=1)
            PlacementService(storage).to_party(foreign, 5)
        before = self.snapshot()
        for host, companion, slot in (("3", str(foreign.pk), 2), ("Necrozma", "5", 2), ("1", "5", 2),
                                      ("3", "3", 2), ("3", "5", 0), ("3", "5", True)):
            with self.subTest(host=host, companion=companion, slot=slot), self.assertRaises(PlacementError):
                self.service.prepare("combine", host, companion, slot)
        self.assertEqual(self.snapshot(), before)
        for update in ({"ability": "Levitate"}, {"is_egg": True}, {"current_hp": 0}):
            original = OwnedPokemon.objects.filter(pk=self.companion.pk).values().get()
            OwnedPokemon.objects.filter(pk=self.companion.pk).update(**update)
            with self.assertRaises(PlacementError):
                self.service.prepare("combine", "3", "5", 2)
            OwnedPokemon.objects.filter(pk=self.companion.pk).update(**{key: original[key] for key in update})

    def test_fusion_references_saved_locks_and_claims_reject_current_sources(self):
        for key, value in (("fusion_forms", [str(self.host.pk)]), ("fusion_id", str(self.companion.pk)),
                           ("fusion_kind", "permanent"), ("morphology", "Fusion"),
                           ("battle_lock", 0), ("battle_id", "stale session"), ("pvp_locked", True)):
            self.owner.attributes.add(key, value)
            try:
                with self.subTest(key=key), self.assertRaises(PlacementError):
                    self.service.prepare("combine", "3", "5", 2)
            finally:
                self.owner.attributes.remove(key)
        token = uuid4()
        PokemonReservations(self.owner).claim("market", [self.companion.pk], token)
        with self.assertRaises(PlacementError):
            self.service.prepare("combine", "3", "5", 2)
        PokemonReservations(self.owner).release("market", token)

    def test_races_against_field_use_placement_release_and_old_cycle_keep_one_custody(self):
        for action in ("field", "placement"):
            operation = self.service.prepare("combine", "3", "5", 2)
            self.trainer.add_item("Potion", 1)
            alternative = (lambda: FieldMedicineUse(self.owner).use("Potion", "3")) if action == "field" else (
                lambda: PlacementService(self.storage).to_box(self.companion))
            outcomes = self.race(lambda: self.service.commit(operation.pk), alternative)
            self.assertNotIn("deadlock", str(outcomes).lower())
            self.assertEqual(OwnedPokemon.objects.filter(trainer=self.trainer).count(), 2)
            if NecrozmaCombination.objects.filter(storage=self.storage).exists():
                self.separate()
            PlacementService(self.storage).to_party(self.companion, 5)
            remaining = self.trainer.get_item_quantity("Potion")
            if remaining:
                self.trainer.remove_item("Potion", remaining)
        stale = self.service.prepare("combine", "3", "5", 2)
        self.combine()
        separate = self.service.prepare("separate", "3")
        outcomes = self.race(lambda: self.service.commit(stale.pk), lambda: self.service.commit(separate.pk))
        self.assertEqual(sum(isinstance(value, PlacementError) for value in outcomes), 1)
        self.assertFalse(NecrozmaCombination.objects.filter(storage=self.storage).exists())
        operation = self.service.prepare("combine", "3", "5", 2)
        outcomes = self.race(lambda: self.service.commit(operation.pk), lambda: PlacementService(self.storage).release(self.companion))
        self.assertEqual(sum(isinstance(value, PlacementError) for value in outcomes), 1)
        self.assertEqual(OwnedPokemon.objects.filter(trainer=self.trainer).count(),
                         2 if NecrozmaCombination.objects.filter(storage=self.storage).exists() else 1)

    def test_actual_base_level_knowledge_and_exp_survive_locked_slots_and_separation(self):
        from pokemon.data.generation import get_valid_moves
        from pokemon.dex import POKEDEX
        from pokemon.names import normalize_name, resolve_dex_entry
        from pokemon.models.stats import add_experience, exp_for_level

        growth = resolve_dex_entry(POKEDEX, "Necrozma").raw.get("growthRate", "medium_fast")
        OwnedPokemon.objects.filter(pk=self.host.pk).update(total_exp=exp_for_level(50, growth))
        future = [(level, {normalize_name(name) for name in get_valid_moves("Necrozma", level)}
                   - {normalize_name(name) for name in get_valid_moves("Necrozma", 50)}) for level in range(51, 101)]
        level, new_names = next((level, names) for level, names in future if names)
        self.combine()
        before = list(ActiveMoveslot.objects.filter(pokemon=self.host).order_by("slot").values())
        pokemon = fresh_owned(self.host.pk)
        add_experience(pokemon, exp_for_level(level, growth) - pokemon.total_exp)
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.host.pk).values_list("level", flat=True).get(), level)
        self.assertEqual(list(ActiveMoveslot.objects.filter(pokemon=self.host).order_by("slot").values()), before)
        self.assertTrue(new_names <= {normalize_name(move.name) for move in pokemon.learned_moves.all()})
        self.separate()
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.host.pk).values_list("level", flat=True).get(), level)
        self.assertTrue(new_names <= {normalize_name(move.name) for move in fresh_owned(self.host.pk).learned_moves.all()})

    def test_unpaired_fused_creation_and_capture_reject_before_ball_or_source_writes(self):
        from types import SimpleNamespace
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.models.core import EncounterPokemon
        from pokemon.services.capture import WildCaptureAttempt

        before = self.snapshot()
        with self.assertRaises(PlacementError):
            create_owned_pokemon("Necrozma-Dusk-Mane", self.trainer, 50, ability="Prism Armor")
        self.assertEqual(before, self.snapshot())
        encounter = EncounterPokemon.objects.create(source_kind="wild", species="Necrozma-Dawn-Wings", level=50,
            ability="Prism Armor", ivs=[0]*6, evs=[0]*6, current_hp=1)
        target = SimpleNamespace(model_id="encounter:" + str(encounter.pk), species=encounter.species)
        attempt = WildCaptureAttempt(target_poke=target, player=self.owner, trainer=self.trainer, ball_name="Master Ball")
        calls = []
        with self.assertRaises(PlacementError):
            attempt.resolve(roll=lambda: calls.append("roll"), consume_ball=lambda: calls.append("debit"))
        self.assertEqual(calls, [])
        self.assertEqual(before, self.snapshot())
        self.assertTrue(EncounterPokemon.objects.filter(pk=encounter.pk).exists())


if __name__ == "__main__":
    try:
        core.database.create_model_tables()
        import importlib
        with connection.schema_editor() as editor:
            importlib.import_module("pokemon.migrations.0041_placement_integrity_triggers").install(apps, editor)
            importlib.import_module("pokemon.migrations.0058_necrozma_integrity").install(apps, editor)
        unittest.main(verbosity=2)
    finally:
        core.database.close()

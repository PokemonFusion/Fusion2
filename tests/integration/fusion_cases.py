"""Actual Fusion commands, atomic failure recovery and races in private PostgreSQL."""

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


class FusionCases(unittest.TestCase):
    """Keep ordinary player commands distinct from deliberate fault/staff setup."""

    def setUp(self):
        self.account = AccountDB.objects.create(username="fusion-qa-" + uuid4().hex)
        self.player, self.alt = [ObjectDB.objects.create(db_key="Fusion QA " + uuid4().hex,
            db_typeclass_path="pokemon.user.User", db_account=self.account) for _ in range(2)]
        self.player.permissions.add("Player")
        self.mon, self.other = [self.create_mon(self.player, species, slot) for species, slot in (
            ("Pikachu", 3), ("Eevee", 6))]
        self.foreign = self.create_mon(self.alt, "Bulbasaur", 2)
        self.player.db.total_exp = 100
        self.messages = []
        self.steps = []
        self.transport = patch.object(self.player, "msg", side_effect=self.messages.append)
        self.transport.start()

    def tearDown(self):
        self.transport.stop()
        TRANSCRIPT.append({"case": self._testMethodName, "commands": self.steps,
                           "permission": list(self.player.permissions.all()), "transport": "captured; no socket",
                           "evidence_kind": "ordinary command replay" if self.steps else "automated service/fault/operator fixture",
                           "durable_fault_boundaries": getattr(self, "durable_fault_boundaries", [])})
        self.assertEqual(list(audit_ownership_v1(apps)), [])

    @staticmethod
    def create_mon(owner, species, slot):
        trainer, _ = Trainer.objects.get_or_create(user=owner,
            defaults={"trainer_number": Trainer.objects.count() + 1})
        storage, _ = UserStorage.objects.get_or_create(user=owner)
        mon = create_owned_pokemon(species, trainer, 20, nature="Hardy", ivs=[1] * 6,
                                  evs=[0] * 6, active_move_names=["Tackle", "Water Gun"])
        OwnedPokemon.objects.filter(pk=mon.pk).update(friendship=255, held_item="", current_hp=3,
                                                      status="slp", sleep_turns=2)
        ActiveMoveslot.objects.filter(pokemon=mon).update(current_pp=2)
        PlacementService(storage).to_party(mon, slot)
        return fresh_owned(mon.pk)

    def command(self, cls, args=""):
        before = self.snapshot()
        start = len(self.messages)
        command = cls()
        command.caller, command.args = self.player, args
        command.func()
        self.steps.append({"input": cls.key + (" " + args if args else ""),
                           "output": self.messages[start:], "before": before, "after": self.snapshot()})
        return self.messages[-1]

    def snapshot(self):
        return {"active": str(BattleRewards.stored_attribute(self.player, "fusion_id") or ""),
                "kind": BattleRewards.stored_attribute(self.player, "fusion_kind"),
                "forms": [str(value) for value in (BattleRewards.stored_attribute(self.player, "fusion_forms") or [])],
                "xp": BattleRewards.stored_attribute(self.player, "total_exp"),
                "placements": list(PokemonPlacement.objects.filter(storage=self.player.storage).order_by("pokemon_id").values(
                    "pokemon_id", "location_type", "slot", "box_id", "box_position"))}

    def test_temp_permanent_switch_unfuse_player_flow_preserves_hp_pp_and_xp(self):
        hp = OwnedPokemon.objects.filter(pk=self.mon.pk).values("current_hp", "status", "sleep_turns").get()
        pp = list(ActiveMoveslot.objects.filter(pokemon=self.mon).values_list("current_pp", flat=True))
        self.assertIn("temporarily fused", self.command(CmdTempFuse, "3"))
        self.assertEqual(PokemonPlacement.objects.get(pokemon=self.mon).location_type, "fusion")
        self.command(CmdUnfuse)
        self.assertEqual(PokemonPlacement.objects.get(pokemon=self.mon).slot, 3)
        self.command(CmdPermFuse, "3 confirm")
        earned = 100 + self.mon.total_exp // 3
        self.assertEqual(BattleRewards.stored_attribute(self.player, "total_exp"), earned)
        self.command(CmdUnfuse)
        self.command(CmdPermFuse, "6 confirm")
        both = earned + self.other.total_exp // 3
        self.command(CmdFusionForms, "1")
        self.assertEqual(BattleRewards.stored_attribute(self.player, "total_exp"), both)
        self.command(CmdUnfuse)
        self.assertEqual(self.player.db.morphology, "Human")
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.mon.pk).values("current_hp", "status", "sleep_turns").get(), hp)
        self.assertEqual(list(ActiveMoveslot.objects.filter(pokemon=self.mon).values_list("current_pp", flat=True)), pp)

    def test_permanent_retry_and_reconnect_cannot_repeat_exp(self):
        operation = uuid4()
        service = FusionTransitions(self.player)
        first = service.run("permanent", self.mon, request_id=operation)
        xp = BattleRewards.stored_attribute(self.player, "total_exp")
        reset_fusion_cache(self.player)
        self.assertEqual(FusionTransitions(ObjectDB.objects.get(pk=self.player.pk)).run(
            "permanent", self.mon, request_id=operation), first)
        self.assertTrue(service.run("permanent", self.mon)[0])
        self.assertEqual(BattleRewards.stored_attribute(self.player, "total_exp"), xp)
        with self.assertRaises(FusionError):
            service.run("temporary", self.other, request_id=operation)

    def test_unfuse_discards_cached_battle_annotations(self):
        """A former temporary source returns as an ordinary party Pokemon."""
        FusionTransitions(self.player).run("temporary", self.mon, slot=3)
        active = fusion.get_active_fusion_pokemon(self.player)
        self.assertTrue(active._pf2_active_fusion)
        FusionTransitions(self.player).run("deactivate")
        self.assertFalse(getattr(active, "_pf2_active_fusion", False))
        self.assertNotIn("_pf2_fusion_level", active.__dict__)

    def test_legacy_permanent_starter_normalizes_without_regranting_progress(self):
        """Known legacy chargen references retain their existing role and identity."""
        self.player.db.fusion_id = str(self.mon.pk).upper()
        self.player.db.fusion_kind = "permanent"
        self.player.db.fusion_forms = [str(self.mon.pk).upper()]
        state = FusionTransitions(self.player).inspect()
        self.assertEqual(state["problems"][0]["code"], "legacy_party_reservation")
        from utils.locks import clear_battle_lock, set_battle_lock

        set_battle_lock(self.player, str(uuid4()))
        clear_battle_lock(self.player)
        for mutation in ("to_box", "release"):
            with self.assertRaisesRegex(PlacementError, "Fusion"):
                getattr(PlacementService(self.player.storage), mutation)(self.mon)
        self.command(CmdUnfuse)
        self.assertEqual(PokemonPlacement.objects.get(pokemon=self.mon).location_type, "fusion")
        self.assertEqual(self.player.db.total_exp, 100)
        self.assertEqual([str(value) for value in self.player.db.fusion_forms], [str(self.mon.pk)])

    def test_permanent_unlock_keeps_legacy_exp_aliases_coherent(self):
        self.player.db.fighter_xp = 100
        self.player.db.fxp = 100
        FusionTransitions(self.player).run("permanent", self.mon)
        xp = 100 + self.mon.total_exp // 3
        for field in ("total_exp", "fighter_xp", "fxp"):
            self.assertEqual(BattleRewards.stored_attribute(self.player, field), xp)
        FusionTransitions(self.player).run("permanent", self.other)
        for field in ("total_exp", "fighter_xp", "fxp"):
            self.assertEqual(BattleRewards.stored_attribute(self.player, field), xp + self.other.total_exp // 3)

    def test_same_account_foreign_source_and_locked_form_are_rejected(self):
        service = FusionTransitions(self.player)
        with self.assertRaises(PlacementError):
            service.run("temporary", self.foreign)
        with self.assertRaises(FusionError):
            service.run("switch", self.mon)
        self.assertEqual(self.snapshot()["active"], "")

    def test_fresh_target_slot_bond_egg_held_and_battle_guards(self):
        for fields in ({"friendship": 0}, {"is_egg": True}, {"held_item": "Oran Berry"}, {"flags": ["breeding"]}):
            previous = OwnedPokemon.objects.filter(pk=self.mon.pk).values().get()
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(**fields)
            with self.assertRaises(PlacementError):
                FusionTransitions(self.player).run("temporary", self.mon, slot=3)
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(**{key: previous[key] for key in fields})
        PlacementService(self.player.storage).to_box(self.mon)
        with self.assertRaises(PlacementError):
            FusionTransitions(self.player).run("temporary", self.mon, slot=3)
        PlacementService(self.player.storage).to_party(self.mon, 3)
        self.player.attributes.add("battle_lock", "later battle")
        try:
            with self.assertRaisesRegex(PlacementError, "battle"):
                FusionTransitions(self.player).run("temporary", self.mon, slot=3)
        finally:
            self.player.attributes.remove("battle_lock")
        self.player.ndb.battle_instance = object()
        try:
            with self.assertRaisesRegex(PlacementError, "battle"):
                FusionTransitions(self.player).run("temporary", self.mon, slot=3)
        finally:
            self.player.ndb.battle_instance = None

    def test_player_command_rechecks_a_target_changed_after_preflight(self):
        from commands.player import cmd_fusion

        original = cmd_fusion.activate_temporary_fusion
        def change_bond_then_activate(character, pokemon, **kwargs):
            """Simulate an independent committed target change after command lookup."""
            OwnedPokemon.objects.filter(pk=pokemon.pk).update(friendship=0)
            return original(character, pokemon, **kwargs)
        before = self.snapshot()
        with patch.object(cmd_fusion, "activate_temporary_fusion", change_bond_then_activate):
            self.assertIn("Bond must be at least 140", self.command(CmdTempFuse, "3"))
        self.assertEqual(self.snapshot(), before)

    def test_slot_target_changed_inside_party_is_rejected(self):
        PlacementService(self.player.storage).to_party(self.mon, 1)
        with self.assertRaisesRegex(PlacementError, "selected party slot"):
            FusionTransitions(self.player).run("permanent", self.mon, slot=3)
        for slot in (True, 0, 7, "1"):
            with self.assertRaisesRegex(PlacementError, "between 1 and 6"):
                FusionTransitions(self.player).run("temporary", self.mon, slot=slot)

    def test_same_account_transfer_approval_is_character_specific(self):
        from pokemon.services.ownership import OwnershipTransfers

        third = ObjectDB.objects.create(db_key="Third ordinary QA " + uuid4().hex,
            db_typeclass_path="pokemon.user.User", db_account=self.account)
        operation = OwnershipTransfers(self.player).prepare(self.alt.pk, [{"pokemon": self.mon.pk,
            "source": self.player.pk, "destination": self.alt.pk}])
        for action in ("approve", "cancel", "commit"):
            with self.assertRaises(PlacementError):
                getattr(OwnershipTransfers(third), action)(operation.pk)
        OwnershipTransfers(self.alt).approve(operation.pk)
        OwnershipTransfers(self.player).commit(operation.pk)
        self.assertEqual(fresh_owned(self.mon.pk).trainer_id, self.alt.trainer.pk)

    def test_switch_failure_restores_prior_temp_form_and_both_placements(self):
        FusionTransitions(self.player).run("temporary", self.mon, slot=3)
        before = self.snapshot()
        original = fusion._set_character_fusion_view
        def fail_after_view(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError("injected after view")
        with patch.object(fusion, "_set_character_fusion_view", fail_after_view):
            with self.assertRaises(RuntimeError):
                FusionTransitions(self.player).run("permanent", self.other)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(str(self.player.db.fusion_id), str(self.mon.pk))
        self.assertEqual(self.player.db.fusion_kind, "temporary")

    def test_permanent_unlock_fault_rolls_back_forms_xp_attributes_and_placement(self):
        before = self.snapshot()
        original = fusion._set_fighter_xp
        def fail_after_xp(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError("injected EXP fault")
        with patch.object(fusion, "_set_fighter_xp", fail_after_xp):
            with self.assertRaises(RuntimeError):
                FusionTransitions(self.player).run("permanent", self.mon)
        self.assertEqual(self.snapshot(), before)
        self.assertIsNone(self.player.db.fusion_id)

    def test_each_durable_write_boundary_restores_the_prior_valid_form(self):
        """Fault every placement, clear/view, EXP alias, form-list and receipt write."""
        for key in ("fighter_xp", "fxp", "xp", "experience"):
            self.player.attributes.add(key, 100)
        service = FusionTransitions(self.player)
        service.run("temporary", self.mon, slot=3)
        before = self.snapshot()
        keys = (*fusion.ACTIVE_FUSION_ATTRS, "morphology", "fusion_forms", "total_exp", "fighter_xp", "fxp", "xp", "experience")
        attributes_before = {key: BattleRewards.stored_attribute(self.player, key) for key in keys}
        original_add = self.player.attributes.add
        original_remove = self.player.attributes.remove
        original_write = PlacementService._write
        boundaries = [("return_source", "placement"), ("reserve_new_source", "placement")]
        boundaries += [(key, "clear") for key in fusion.ACTIVE_FUSION_ATTRS]
        boundaries += [(key, "add") for key in ("fusion_forms", "total_exp", "fighter_xp", "fxp", "xp", "experience",
                                                "fusion_id", "fusion_species", "fusion_ability", "fusion_nature", "fusion_kind", "morphology")]
        boundaries.append(("receipt", "add"))
        self.durable_fault_boundaries = []
        for key, kind in boundaries:
            with self.subTest(boundary=key, kind=kind):
                def fail_add(name, value, *args, **kwargs):
                    """Raise after a real Attribute insert/update, including the receipt."""
                    result = original_add(name, value, *args, **kwargs)
                    if name == key or (key == "receipt" and kwargs.get("category") == "fusion_transitions"):
                        raise RuntimeError("injected durable Attribute fault")
                    return result
                def fail_remove(name, *args, **kwargs):
                    """Raise after a real clear, so rolled-back caches must also recover."""
                    result = original_remove(name, *args, **kwargs)
                    if name == key:
                        raise RuntimeError("injected durable clear fault")
                    return result
                def fail_placement(placement_service, pokemon, storage, current, location, **kwargs):
                    """Raise after either the old return or the new reservation commits locally."""
                    result = original_write(placement_service, pokemon, storage, current, location, **kwargs)
                    if ((key == "return_source" and pokemon.pk == self.mon.pk and location == "party")
                            or (key == "reserve_new_source" and pokemon.pk == self.other.pk and location == "fusion")):
                        raise RuntimeError("injected durable placement fault")
                    return result
                target, method, replacement = ((self.player.attributes, "add", fail_add) if kind == "add" else
                    (self.player.attributes, "remove", fail_remove) if kind == "clear" else
                    (PlacementService, "_write", fail_placement))
                with patch.object(target, method, replacement), self.assertRaisesRegex(RuntimeError, "injected durable"):
                    service.run("permanent", self.other)
                self.assertEqual(self.snapshot(), before)
                self.assertEqual({name: BattleRewards.stored_attribute(self.player, name) for name in keys}, attributes_before)
                self.assertEqual(str(self.player.db.fusion_id), str(self.mon.pk))
                self.assertFalse(service.inspect()["problems"])
                self.durable_fault_boundaries.append(kind + ":" + key)

    def test_full_party_temp_return_uses_box_without_losing_source(self):
        FusionTransitions(self.player).run("temporary", self.mon, slot=3)
        for slot in range(1, 6):
            self.create_mon(self.player, "Squirtle", slot)
        self.command(CmdUnfuse)
        self.assertEqual(PokemonPlacement.objects.get(pokemon=self.mon).location_type, "box")

    def test_system_reservation_blocks_temp_and_permanent(self):
        PokemonReservations(self.player).claim("daycare", [self.mon.pk], uuid4())
        for action in ("temporary", "permanent"):
            with self.assertRaisesRegex(PlacementError, "reserved"):
                FusionTransitions(self.player).run(action, self.mon)

    def race(self, *actions):
        """Use independent connections and a shared start barrier for real row locks."""
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

    def test_concurrent_permanent_unlock_grants_exp_once(self):
        self.race(lambda: FusionTransitions(self.player).run("permanent", self.mon),
                  lambda: FusionTransitions(self.player).run("permanent", self.mon))
        self.assertEqual(BattleRewards.stored_attribute(self.player, "total_exp"), 100 + self.mon.total_exp // 3)
        self.assertEqual([str(value) for value in self.player.db.fusion_forms], [str(self.mon.pk)])

    def test_concurrent_activation_and_storage_or_release_never_lose_source(self):
        for mutation in ("to_box", "release"):
            mon = self.create_mon(self.player, "Squirtle", 1)
            pokemon_id = mon.pk
            results = self.race(lambda: FusionTransitions(self.player).run("temporary", mon, slot=1),
                lambda: getattr(PlacementService(self.player.storage), mutation)(mon))
            self.assertEqual(sum(isinstance(result, PlacementError) for result in results), 1)
            self.assertFalse(FusionTransitions(self.player).inspect()["problems"])
            FusionTransitions(self.player).run("deactivate")
            if OwnedPokemon.objects.filter(pk=pokemon_id).exists():
                PlacementService(self.player.storage).release(fresh_owned(pokemon_id))

    def test_fusion_vs_consent_transfer_has_one_authoritative_reservation(self):
        from pokemon.services.ownership import OwnershipTransfers

        results = self.race(lambda: FusionTransitions(self.player).run("permanent", self.mon),
            lambda: OwnershipTransfers(self.player).prepare(self.alt.pk, [{"pokemon": self.mon.pk,
                "source": self.player.pk, "destination": self.alt.pk}]))
        self.assertEqual(sum(isinstance(result, PlacementError) for result in results), 1)
        self.assertFalse(FusionTransitions(self.player).inspect()["problems"])

    def test_concurrent_different_temp_forms_and_unfuse_are_coherent(self):
        self.race(lambda: FusionTransitions(self.player).run("temporary", self.mon, slot=3),
                  lambda: FusionTransitions(self.player).run("temporary", self.other, slot=6))
        self.assertEqual(self.player.storage.placements.filter(location_type="fusion").count(), 1)
        self.assertFalse(FusionTransitions(self.player).inspect()["problems"])
        active = fresh_owned(BattleRewards.stored_attribute(self.player, "fusion_id"))
        self.race(lambda: FusionTransitions(self.player).run("deactivate"),
                  lambda: FusionTransitions(self.player).run("temporary", active))
        self.assertFalse(FusionTransitions(self.player).inspect()["problems"])

    def test_missing_foreign_references_are_inspectable_and_recover_only_refs(self):
        self.player.db.fusion_id = str(self.foreign.pk)
        self.player.db.fusion_forms = [str(self.foreign.pk), str(uuid4())]
        self.player.db.fusion_kind = "permanent"
        service = FusionTransitions(self.player)
        state = service.inspect()
        self.assertEqual({p["code"] for p in state["problems"]}, {"missing_reference", "foreign_reference"})
        with self.assertRaises(FusionError):
            service.run("deactivate")
        with self.assertRaises(FusionError):
            service.clear_invalid_references("stale fingerprint", operator_note="controlled QA")
        repaired = service.clear_invalid_references(state["fingerprint"], operator_note="controlled QA")
        self.assertFalse(repaired["problems"])
        self.assertEqual(fresh_owned(self.foreign.pk).trainer_id, self.alt.trainer.pk)
        self.assertEqual(self.player.db.total_exp, 100)

    def test_unreferenced_owned_reservation_is_not_automatically_returned(self):
        PlacementService(self.player.storage).reserve_for_fusion(self.mon)
        service = FusionTransitions(self.player)
        state = service.inspect()
        self.assertEqual(state["problems"][0]["code"], "unreferenced_reservation")
        with self.assertRaises(FusionError):
            service.clear_invalid_references(state["fingerprint"], operator_note="controlled QA")
        self.assertEqual(PokemonPlacement.objects.get(pokemon=self.mon).location_type, "fusion")

    def test_operator_inspection_is_read_only_and_recovery_requires_exact_state(self):
        """The shipped staff tool exposes no automatic custody or progression repair."""
        from django.core.management import call_command
        from django.core.management.base import CommandError
        from io import StringIO

        self.player.db.fusion_id = str(uuid4())
        self.player.db.fusion_kind = "permanent"
        before = self.snapshot()
        output = StringIO()
        call_command("audit_fusion_state", str(self.player.pk), stdout=output)
        state = json.loads(output.getvalue())
        self.assertEqual(self.snapshot(), before)
        with self.assertRaises(CommandError):
            call_command("audit_fusion_state", str(self.player.pk), clear_invalid_references=True,
                         fingerprint="stale", operator_note="Controlled tagged QA", stdout=StringIO())
        call_command("audit_fusion_state", str(self.player.pk), clear_invalid_references=True,
                     fingerprint=state["fingerprint"], operator_note="Controlled tagged QA", stdout=StringIO())
        self.assertEqual(self.snapshot()["active"], "")


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
            from commands.player.cmd_fusion import CmdTempFuse, CmdPermFuse, CmdFusionForms, CmdUnfuse
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.models.storage import PokemonPlacement, UserStorage
        from pokemon.models.trainer import Trainer
        from pokemon.services.battle_rewards import BattleRewards
        from pokemon.services.fusion_transitions import FusionError, FusionTransitions, reset_fusion_cache
        from pokemon.services.ownership import fresh_owned, PokemonReservations
        from pokemon.services.ownership_audit import audit_ownership_v1
        from pokemon.services.placement import PlacementError, PlacementService
        from utils import fusion
        try:
            unittest.main(verbosity=2)
        finally:
            if os.environ.get("PF2_FUSION_PLAYER_EVIDENCE"):
                Path(os.environ["PF2_FUSION_PLAYER_EVIDENCE"]).write_text(
                    json.dumps(TRANSCRIPT, default=str, indent=2), encoding="utf-8")

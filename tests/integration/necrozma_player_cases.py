"""Actual hunt/capture, native combine menus, field items and full-turn battles.

Charts, stock and wallets are separate disposable setup. Ordinary input uses
production commands and menu nodes. Captured transport is local automation,
not an intentionally released live socket walkthrough.
"""

from copy import deepcopy
import importlib
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from isolated_postgres import IsolatedPostgres
import mega_evolution_cases as core


class NecrozmaPlayerCases(unittest.TestCase):
    """Retain source, input, SQL, runtime and effect observations independently."""

    command = core.MegaEvolutionCases.command
    state = core.MegaEvolutionCases.state
    native = core.MegaEvolutionCases.native
    buy = core.MegaEvolutionCases.buy
    record = core.MegaEvolutionCases.record
    launch = core.MegaEvolutionCases.launch
    rebuild = core.MegaEvolutionCases.rebuild

    def reply(self, text):
        """Retain exact ordinary confirmation/store input as separate evidence."""
        before, start = self.observation(), len(self.player.messages)
        result = core.MegaEvolutionCases.reply(self, text)
        core.EVIDENCE.append({"case": self._testMethodName, "event": "menu-reply", "input": text,
            "before": before, "after": self.observation(),
            "messages": list(map(str, self.player.messages[start:]))})
        return result

    def setUp(self):
        """Use ordinary real characters and production acquisition boundaries."""
        core.MegaEvolutionCases.setUp(self)
        self.room.db.is_pokemon_center = True
        for player in self.players:
            core.acquisition.ObjectDB.objects.filter(pk=player.character.pk).update(db_location_id=self.room.pk)
        self.host, self.companion = None, None

    def tearDown(self):
        """Verify final canonical state and end only this fixture's battles/menus."""
        core.MegaEvolutionCases.tearDown(self)
        self.assertEqual(list(audit_placements_v3(apps)), [])

    def test_command_is_available_in_actual_pokemon_core_cmdset(self):
        """The accepted player class is reachable through the normal registration."""
        import evennia
        from evennia.commands.command import Command
        from evennia.commands.cmdset import CmdSet

        with patch.object(evennia, "Command", Command), patch.object(evennia, "CmdSet", CmdSet):
            from commands.cmdsets.pokemon_core import PokemonCoreCmdSet
            from commands.player.cmd_necrozma import CmdNecrozma
        commands = PokemonCoreCmdSet()
        self.assertIsInstance(commands.get("+necrozma"), CmdNecrozma)

    def observation(self):
        """Include both source rows and PP history, not only the active host."""
        result = core.MegaEvolutionCases.observation(self)
        result["native_pairs"] = list(NecrozmaCombination.objects.filter(storage=self.player.storage).values())
        result["native_resources"] = list(NecrozmaResource.objects.filter(host__trainer=self.player.trainer).values())
        result["native_placements"] = list(PokemonPlacement.objects.filter(storage=self.player.storage).order_by("pokemon_id").values())
        return result

    def capture_source(self, species, slot, *, level=50):
        """Author a named chart, then use actual +hunt and +item Master Ball."""
        self.room.db.allow_hunting = True
        self.room.db.npc_chance, self.room.db.encounter_rate = 0, 100
        self.room.db.hunt_chart = [{"name": species, "min_level": level, "max_level": level, "weight": 1}]
        self.buy("Master Ball", price=1000, quantity=1)
        before = set(core.OwnedPokemon.objects.filter(trainer=self.player.trainer).values_list("pk", flat=True))
        import time
        now = max(time.time(), float(getattr(self.player.ndb, "last_hunt_time", 0) or 0) + 4)
        # Controlled clock advances past the real three-second cooldown; no
        # cooldown state, encounter selection or capture outcome is bypassed.
        with patch("world.hunt_system.time", SimpleNamespace(time=lambda: now)):
            self.record("hunt")
        self.session = self.player.ndb.battle_instance
        self.assertIsNotNone(self.session, self.player.messages[-6:])
        self.assertEqual(str(self.session.battle.participants[1].active[0].species), species)
        self.record("item", "Master Ball")
        caught = core.OwnedPokemon.objects.filter(trainer=self.player.trainer).exclude(pk__in=before).get()
        self.mons.append(caught)
        self.assertEqual(caught.species, species)
        self.assertEqual(self.player.trainer.get_item_quantity("Master Ball"), 0)
        self.session.end()
        self.session = None
        for placement in self.player.storage.placements.filter(location_type="party", slot=slot):
            core.PlacementService(self.player.storage).to_box(placement.pokemon)
        core.PlacementService(self.player.storage).to_party(caught, slot)
        return caught

    def acquire_pair(self, companion, *, level=50):
        """Acquire both genuine source UUIDs rather than grant an already fused row."""
        self.host = self.capture_source("Necrozma", 3, level=level)
        self.mon = self.host
        self.companion = self.capture_source(companion, 5, level=level)
        self.mon = self.host
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.host.pk).values_list("ability", flat=True).get(), "Prism Armor")
        self.partner_before = OwnedPokemon.objects.filter(pk=self.companion.pk).values().get()

    def combine(self, slot=2):
        """Review exact source identities and confirm with the actual menu command."""
        self.record("necrozma", f"combine 3=5/{slot}")
        text = "\n".join(map(str, self.player.messages[-8:]))
        self.assertIn(str(self.host.pk), text)
        self.assertIn(str(self.companion.pk), text)
        self.assertIn("Displaced slot", text)
        self.reply("yes")
        self.assertIsNone(self.player.ndb._evmenu)
        self.assertTrue(NecrozmaCombination.objects.filter(host=self.host).exists(), self.player.messages[-6:])

    def separate(self):
        self.record("necrozma", "separate 3")
        self.reply("yes")
        self.assertFalse(NecrozmaCombination.objects.filter(host=self.host).exists(), self.player.messages[-6:])
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.companion.pk).values().get(), self.partner_before)

    def pp(self):
        slot = ActiveMoveslot.objects.get(pokemon=self.host, slot=2)
        resource = NecrozmaResource.objects.get(host=self.host, source=slot.move.name)
        self.assertEqual(slot.current_pp, resource.current_pp)
        return slot.current_pp

    def field_flow(self, companion):
        self.acquire_pair(companion)
        ordinary = list(ActiveMoveslot.objects.filter(pokemon=self.host).order_by("slot").values("slot", "move_id", "current_pp"))
        self.combine()
        self.record("necrozma", "inspect 3")
        self.record("necrozma", "inspect " + str(self.companion.pk))
        ActiveMoveslot.objects.filter(pokemon=self.host, slot=2).update(current_pp=0)  # separately labelled depleted-PP fixture
        self.assertEqual(self.pp(), 0)
        self.buy("Ether", price=100, quantity=1)
        source = ActiveMoveslot.objects.get(pokemon=self.host, slot=2).move.name
        self.record("use", "Ether=3/" + source)
        self.assertEqual(self.pp(), 5)
        self.buy("PP Max", price=100, quantity=1)
        self.record("use", "PP Max=3")
        self.record("use", "2")
        self.assertEqual(self.pp(), 8)
        ActiveMoveslot.objects.filter(pokemon=self.host, slot=2).update(current_pp=0)
        self.separate()
        self.assertEqual(list(ActiveMoveslot.objects.filter(pokemon=self.host).order_by("slot").values("slot", "move_id", "current_pp")), ordinary)
        self.combine()
        self.assertEqual(self.pp(), 0)
        self.buy("Leppa Berry", price=100, quantity=1)
        self.record("use", "Leppa Berry=3/" + source)
        self.assertEqual(self.pp(), 8)
        self.separate()

    def test_dusk_actual_acquisition_menu_field_pp_items_and_zero_cycle(self):
        self.field_flow("Solgaleo")

    def test_dawn_actual_acquisition_menu_field_pp_items_and_zero_cycle(self):
        self.field_flow("Lunala")

    def test_linked_rare_candy_training_healing_and_manual_slot_edits(self):
        self.acquire_pair("Solgaleo")
        # Captures can legitimately have a perfect Attack IV, where a Bottle
        # Cap correctly has no effect. Label a useful training precondition;
        # keep the ordinarily captured source UUID and all remaining genetics.
        ivs = list(OwnedPokemon.objects.filter(pk=self.host.pk).values_list("ivs", flat=True).get())
        core.EVIDENCE.append({"case": self._testMethodName, "event": "training-fixture-precondition",
            "host": str(self.host.pk), "before_ivs": ivs[:], "attack_iv": 0})
        ivs[1] = 0
        OwnedPokemon.objects.filter(pk=self.host.pk).update(ivs=ivs)
        ordinary = list(ActiveMoveslot.objects.filter(pokemon=self.host).order_by("slot").values("slot", "move_id", "current_pp"))
        self.combine()
        from pokemon.services.ownership import fresh_owned
        from pokemon.services.move_management import apply_active_moveset, initialize_generated_moveset
        from pokemon.services.placement import PlacementError

        active = list(ActiveMoveslot.objects.filter(pokemon=self.host).order_by("slot").values("slot", "move_id", "current_pp"))
        self.buy("Rare Candy", price=100, quantity=1)
        self.record("use", "Rare Candy=3")
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.host.pk).values_list("level", flat=True).get(), 51)
        self.assertIsNone(self.player.ndb._evmenu)
        self.assertEqual(list(ActiveMoveslot.objects.filter(pokemon=self.host).order_by("slot").values("slot", "move_id", "current_pp")), active)
        self.buy("Protein", price=100, quantity=1)
        self.record("use", "Protein=3")
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.host.pk).values_list("evs", flat=True).get()[1], 10)
        self.buy("Bottle Cap", price=100, quantity=1)
        self.record("use", "Bottle Cap=3/Atk")
        self.assertIn("hypertrained:attack", OwnedPokemon.objects.filter(pk=self.host.pk).values_list("flags", flat=True).get())
        self.buy("PP Up", price=100, quantity=1)
        self.record("use", "PP Up=3")
        self.record("use", "2")
        self.assertEqual(self.pp(), 6)
        for call in (lambda: apply_active_moveset(fresh_owned(self.host.pk)),
                     lambda: initialize_generated_moveset(fresh_owned(self.host.pk), active_move_names=["Tackle"])):
            with self.assertRaises(PlacementError):
                call()
        ActiveMoveslot.objects.filter(pokemon=self.host, slot=2).update(current_pp=0)
        pokemon = fresh_owned(self.host.pk)
        pokemon.heal()
        self.assertEqual(pokemon.current_hp, pokemon.get_max_hp())
        self.assertEqual(self.pp(), 6)
        self.separate()
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.host.pk).values_list("level", flat=True).get(), 51)
        self.assertEqual(list(ActiveMoveslot.objects.filter(pokemon=self.host).order_by("slot").values("slot", "move_id", "current_pp")), ordinary)

    def test_cancel_invalid_input_companion_freeze_and_stale_menu(self):
        self.acquire_pair("Lunala")
        before = self.observation()
        self.record("necrozma", "combine 3=5/2")
        self.reply("no")
        self.assertEqual(self.observation(), before)
        self.record("necrozma", "combine 3=5/2")
        OwnedPokemon.objects.filter(pk=self.host.pk).update(nickname="Changed during review")
        self.reply("yes")
        self.assertFalse(NecrozmaCombination.objects.filter(host=self.host).exists())
        self.assertIn("stale", "\n".join(map(str, self.player.messages[-6:])))
        self.combine()
        self.buy("Potion", price=100, quantity=1)
        before = self.observation()
        self.record("use", "Potion=" + str(self.companion.pk))
        self.assertEqual(before, self.observation())
        self.assertEqual(self.player.trainer.get_item_quantity("Potion"), 1)
        self.record("necrozma", "inspect " + str(self.companion.pk))
        self.assertIn("reserved companion", "\n".join(map(str, self.player.messages[-3:])))
        self.separate()

    def test_menu_success_waits_for_outer_commit_and_exact_retry_has_one_effect(self):
        from django.db import transaction
        from pokemon.models.necrozma import NecrozmaOperation

        self.acquire_pair("Lunala")
        self.record("necrozma", "combine 3=5/2")
        operation = NecrozmaOperation.objects.filter(storage=self.player.storage, state="pending").latest("created_at")
        start = len(self.player.messages)
        with self.assertRaisesRegex(RuntimeError, "outer rollback"), transaction.atomic():
            self.reply("yes")
            self.assertFalse(any("became Necrozma" in str(msg) for msg in self.player.messages[start:]))
            raise RuntimeError("outer rollback")
        self.assertFalse(NecrozmaCombination.objects.filter(host=self.host).exists())
        self.assertEqual(NecrozmaOperation.objects.get(pk=operation.pk).state, "pending")
        self.record("necrozma", "review " + str(operation.pk))
        self.reply("yes")
        self.assertEqual(sum("became Necrozma" in str(msg) for msg in self.player.messages[start:]), 1)
        from menus.necrozma import _confirm

        _confirm(self.player, "yes", request_id=str(operation.pk))
        self.assertEqual(sum("became Necrozma" in str(msg) for msg in self.player.messages[start:]), 1)
        self.separate()

    def battle_flow(self, companion, crystal, signature):
        self.acquire_pair(companion)
        self.combine()
        self.buy(crystal, price=100, quantity=1)
        self.record("hold", "3=" + crystal)
        self.launch()
        source = ActiveMoveslot.objects.get(pokemon=self.host, slot=2).move.name
        with patch.object(self.session, "maybe_run_turn"):
            self.record("attack", source + " B1")
            self.record("attack", "Growl A1", side=1)
        self.session.execute_persistent_turn()
        self.assertEqual(self.pp(), 4)
        self.rebuild()
        with patch.object(self.session, "maybe_run_turn"):
            self.record("switch", "4")
            self.record("attack", "Growl A1", side=1)
        self.session.execute_persistent_turn()
        self.assertNotEqual(self.session.battle.participants[0].active[0].model_id, "owned:" + str(self.host.pk))
        self.rebuild()
        with patch.object(self.session, "maybe_run_turn"):
            self.record("switch", "3")
            self.record("attack", "Growl A1", side=1)
        self.session.execute_persistent_turn()
        self.assertEqual(self.session.battle.participants[0].active[0].model_id, "owned:" + str(self.host.pk))
        self.assertEqual(self.pp(), 4)
        self.rebuild()
        before = self.session.battle.participants[1].active[0].hp
        with patch.object(self.session, "maybe_run_turn"):
            self.record("zmove", source + "=B1")
            self.record("attack", "Growl A1", side=1)
        self.assertTrue(self.session.battle.z_pending, self.player.messages[-6:])
        self.session.execute_persistent_turn()
        self.assertEqual(self.pp(), 3)
        self.assertEqual(self.session.battle.z_used, {"A"})
        self.assertLess(self.session.battle.participants[1].pokemons[0].hp, before)
        self.assertIn(signature, "\n".join(map(str, self.player.messages)))
        self.rebuild()
        self.session.end()
        self.session = None
        self.assertTrue(NecrozmaCombination.objects.filter(host=self.host).exists())
        self.separate()
        from pokemon.names import normalize_name

        self.assertEqual(normalize_name(OwnedPokemon.objects.filter(pk=self.host.pk).values_list("held_item", flat=True).get()), normalize_name(crystal))

    def test_dusk_ordinary_attack_rebuild_existing_signature_and_separation(self):
        self.battle_flow("Solgaleo", "Solganium Z", "Searing Sunraze Smash")

    def test_dawn_ordinary_attack_rebuild_existing_signature_and_separation(self):
        self.battle_flow("Lunala", "Lunalium Z", "Menacing Moonraze Maelstrom")

    def signature_controls(self, companion, crystal, source):
        """Apply existing doubles effects to a genuinely acquired, paired holder."""
        from z_signature_cases import SignatureZCases
        from pokemon.battle.z_profiles import ZProfiles

        # Ordinary authored level-30 sources keep full unprotected damage below
        # the level-100 target's real HP. Overkill clamps otherwise make an
        # exact quarter-HP comparison invalid for some captured IVs/natures.
        self.acquire_pair(companion, level=30)
        self.combine()
        profile = ZProfiles.get(crystal, source)
        self.fixture_native = SignatureZCases.fixture_native.__get__(self)
        damage = {}
        for control in ("active", "protect", "sleep", "immune"):
            effect = SignatureZCases.flow(self, profile, control, captured=self.host,
                native="Necrozma-Dusk-Mane" if companion == "Solgaleo" else "Necrozma-Dawn-Wings")
            damage[control] = effect["damage"]
            self.assertEqual(self.pp(), 5 - sum(name != "sleep" for name in damage))
            self.assertEqual(OwnedPokemon.objects.filter(pk=self.companion.pk).values().get(), self.partner_before)
            if control == "sleep":
                # The same real host persists between controls. Cure the
                # explicitly seeded sleep before the following immunity case.
                self.buy("Awakening", price=100, quantity=1)
                self.record("use", "Awakening=3")
                self.assertNotEqual(OwnedPokemon.objects.filter(pk=self.host.pk).values_list("status", flat=True).get(), "slp")
        self.assertEqual(damage["protect"], max(1, damage["active"] // 4))
        self.assertEqual(damage["sleep"], 0)
        # These two signatures ignore breakable Wonder Guard; Ghost still
        # respects an actual Normal-type immunity. The shared harness checks it.
        self.assertEqual(damage["immune"] == 0, companion == "Lunala")
        self.separate()

    def test_dusk_doubles_protection_prevention_and_ability_boundary(self):
        self.signature_controls("Solgaleo", "Solganium Z", "Sunsteel Strike")

    def test_dawn_doubles_protection_prevention_and_type_immunity(self):
        self.signature_controls("Lunala", "Lunalium Z", "Moongeist Beam")

    def test_faint_revive_rebuild_and_concede_preserve_native_pair(self):
        """A fainted reserved host remains the same row through ordinary Revive."""
        self.acquire_pair("Lunala")
        self.combine()
        self.buy("Revive", price=100, quantity=1)
        self.launch()
        holder = self.session.battle.participants[0].active[0]
        holder.hp, holder.is_fainted = 0, True  # explicitly depleted runtime fixture
        self.session.battle.run_faint()
        self.session._sync_player_pokemon_state(strict=True)
        self.session._sync_active_battle_state()
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.host.pk).values_list("current_hp", flat=True).get(), 0)
        with patch.object(self.session, "maybe_run_turn"):
            self.record("item", "Revive=3")
            self.record("attack", "Growl A1", side=1)
        self.session.execute_persistent_turn()
        self.assertGreater(holder.hp, 0)
        self.assertEqual(self.player.trainer.get_item_quantity("Revive"), 0)
        self.assertEqual(self.pp(), 5)
        self.rebuild()
        self.record("concede", "yes")
        self.assertIsNone(self.player.ndb.battle_instance)
        self.assertTrue(NecrozmaCombination.objects.filter(host=self.host).exists())
        self.session = None
        self.separate()

    def test_native_stacking_corrupt_proof_and_checkpoint_rollback_keep_pair_and_pp(self):
        self.acquire_pair("Solgaleo")
        self.combine()
        self.buy("Solganium Z", price=100, quantity=1)
        self.record("hold", "3=Solganium Z")
        self.launch()
        actor = self.session.battle.participants[0].active[0]
        before = self.observation()
        self.record("tera")
        self.record("mega")
        self.assertEqual(self.observation(), before)
        owner = self.player.character
        other = next(mon.pk for mon in self.mons if mon.pk not in {self.host.pk, self.companion.pk})
        for key, value in (("fusion_id", str(other)), ("fusion_kind", "temporary"), ("morphology", "Fusion")):
            owner.attributes.add(key, value)  # separately labelled invalid-controller precondition
            try:
                self.record("zmove", "Sunsteel Strike=B1")
                self.assertFalse(self.session.battle.z_pending)
                self.assertEqual(self.pp(), 5)
            finally:
                owner.attributes.remove(key)
        proof = deepcopy(actor.native_origin)
        actor.native_origin["necrozma"]["lifecycle"] = "old forged cycle"
        self.record("zmove", "Sunsteel Strike=B1")
        self.assertFalse(self.session.battle.z_pending)
        actor.native_origin = proof
        with patch.object(self.session, "maybe_run_turn"):
            self.record("zmove", "Sunsteel Strike=B1")
            self.record("attack", "Growl A1", side=1)
        before, old_pp = self.observation(), self.pp()
        original = self.session.storage.set
        def fail(key, value):
            if key == "state":
                raise RuntimeError("Injected native checkpoint failure")
            return original(key, value)
        with patch.object(self.session.storage, "set", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "checkpoint failure"):
                self.session.execute_persistent_turn()
        self.assertEqual(self.pp(), old_pp)
        self.assertFalse(self.session.battle.z_used)
        self.assertEqual(self.session.battle.z_pending, before["battle"]["state"]["z_pending"])
        self.session.execute_persistent_turn()
        self.assertEqual(self.pp(), old_pp - 1)
        self.assertEqual(self.session.battle.z_used, {"A"})
        self.session.end()
        self.session = None
        self.separate()

    def test_wild_zero_pp_battle_ether_and_normal_flee_keep_native_pair(self):
        self.acquire_pair("Solgaleo")
        self.combine()
        self.buy("Solganium Z", price=100, quantity=1)
        self.record("hold", "3=Solganium Z")
        self.buy("Ether", price=100, quantity=1)
        ActiveMoveslot.objects.filter(pokemon=self.host, slot=2).update(current_pp=0)
        self.launch(kind="wild")
        self.record("zmove", "Sunsteel Strike=B1")
        self.assertFalse(self.session.battle.z_pending)
        self.assertFalse(self.session.battle.z_used)
        self.assertEqual(self.pp(), 0)
        self.record("item", "Ether=3/Sunsteel Strike")
        self.assertEqual(self.pp(), 5)
        self.assertEqual(self.player.trainer.get_item_quantity("Ether"), 0)
        self.rebuild()
        for _ in range(8):
            if self.player.ndb.battle_instance is None:
                break
            self.record("flee")
        self.assertIsNone(self.player.ndb.battle_instance, self.player.messages[-6:])
        self.assertTrue(NecrozmaCombination.objects.filter(host=self.host).exists())
        self.assertEqual(self.pp(), 5)
        self.session = None
        self.separate()

    def test_both_native_zero_pp_sources_reject_ordinary_attacks(self):
        """Real ordinary commands cannot use dex capacity as saved source PP."""
        for companion, source in (("Solgaleo", "Sunsteel Strike"), ("Lunala", "Moongeist Beam")):
            with self.subTest(companion=companion):
                self.acquire_pair(companion)
                self.combine()
                ActiveMoveslot.objects.filter(pokemon=self.host, slot=2).update(current_pp=0)
                self.launch(kind="wild")
                before = self.observation()
                start = len(self.player.messages)
                self.record("attack", source)
                self.assertIn("cannot use that move", "\n".join(map(str, self.player.messages[start:])))
                self.assertFalse(self.session.state.declare)
                self.assertFalse(self.session.battle.participants[0].pending_action)
                self.assertEqual(self.pp(), 0)
                self.assertEqual(self.observation(), before)
                self.session.end()
                self.session = None
                self.separate()

    def test_old_pp_prompt_cannot_boost_a_new_native_lifecycle(self):
        self.acquire_pair("Lunala")
        self.combine()
        self.buy("PP Up", price=100, quantity=1)
        self.record("use", "PP Up=3")
        first = self.player.ndb.pending_pp_item
        self.assertTrue(first)
        self.separate()
        self.combine()
        self.record("use", "2")
        self.assertIn("stale", "\n".join(map(str, self.player.messages[-4:])))
        self.assertEqual(self.player.trainer.get_item_quantity("PP Up"), 1)
        self.assertEqual(self.pp(), 5)
        self.record("use", "PP Up=3")
        self.record("use", "2")
        self.assertEqual(self.player.trainer.get_item_quantity("PP Up"), 0)
        self.assertEqual(self.pp(), 6)
        self.separate()


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        core.load_runtime()
        from django.apps import apps
        from django.db import connection
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.models.necrozma import NecrozmaCombination, NecrozmaResource
        from pokemon.models.storage import PokemonPlacement
        from pokemon.services.placement_audit import audit_placements_v3

        with connection.schema_editor() as editor:
            importlib.import_module("pokemon.migrations.0041_placement_integrity_triggers").install(apps, editor)
            importlib.import_module("pokemon.migrations.0058_necrozma_integrity").install(apps, editor)
        import evennia
        from evennia.commands.command import Command
        from evennia.commands.cmdset import CmdSet
        with patch.object(evennia, "Command", Command), patch.object(evennia, "CmdSet", CmdSet):
            from commands.player import cmd_necrozma, cmd_battle_zmove, cmd_battle_concede
        core.acquisition.COMMANDS.update({"necrozma": (cmd_necrozma, cmd_necrozma.CmdNecrozma),
            "zmove": (cmd_battle_zmove, cmd_battle_zmove.CmdBattleZMove),
            "concede": (cmd_battle_concede, cmd_battle_concede.CmdBattleConcede)})
        try:
            result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(NecrozmaPlayerCases))
        finally:
            if os.environ.get("PF2_NECROZMA_EVIDENCE"):
                Path(os.environ["PF2_NECROZMA_EVIDENCE"]).write_text(json.dumps(core.EVIDENCE, indent=2, default=str), encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())

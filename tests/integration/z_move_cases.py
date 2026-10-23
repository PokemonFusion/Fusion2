"""Owned source PP, ordinary +zmove input and full-turn recovery in private SQL."""

from copy import deepcopy
import json
import os
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import mega_evolution_cases as core
from mega_stone_cases import MegaStoneCases


class ZMoveCases(unittest.TestCase):
    """Reuse real native/source/shop/player adapters without staff battle input."""

    command = core.MegaEvolutionCases.command
    reply = core.MegaEvolutionCases.reply
    state = core.MegaEvolutionCases.state
    native = core.MegaEvolutionCases.native
    buy = core.MegaEvolutionCases.buy
    record = core.MegaEvolutionCases.record
    observation = core.MegaEvolutionCases.observation
    launch = core.MegaEvolutionCases.launch
    rebuild = core.MegaEvolutionCases.rebuild
    fixture_native = MegaStoneCases.fixture_native

    def setUp(self):
        """Only setup creates tagged native sources and the ordinary transports."""
        core.MegaEvolutionCases.setUp(self)

    def tearDown(self):
        """Use the production ending route and remove only disposable source objects."""
        core.MegaEvolutionCases.tearDown(self)

    def equip(self):
        """Buy exactly one copy and equip it using the actual held-item command."""
        self.buy("Normalium Z", price=10000, quantity=1)
        self.record("hold", "3=Normalium Z")
        self.assertEqual(self.player.trainer.get_item_quantity("Normalium Z"), 0)

    def resolve(self, *, z=True, rebuild=False):
        """Retain exact source command/output/state around one ordinary full turn."""
        with patch.object(self.session, "maybe_run_turn"):
            self.record("zmove" if z else "attack", "Tackle=B1" if z else "Tackle B1")
            if rebuild:
                self.rebuild()
            self.record("attack", "Growl A1", side=1)
        before = self.observation()
        start = len(self.player.messages)
        self.session.execute_persistent_turn()
        core.EVIDENCE.append(
            {
                "case": self._testMethodName,
                "event": "complete-z-turn" if z else "ordinary-control-turn",
                "before": before,
                "after": self.observation(),
                "messages": list(map(str, self.player.messages[start:])),
            }
        )

    def test_purchase_discovery_queue_rebuild_effect_source_pp_cleanup_and_return(self):
        """The crystal stays reusable; one queued MOVE spends one actual Tackle PP."""
        self.equip()
        self.launch()
        before = self.observation()
        self.record("zmove")
        self.assertEqual(self.observation(), before)
        self.resolve(rebuild=True)
        battle = self.session.battle
        holder, foe = (part.active[0] for part in battle.participants)
        self.assertEqual(battle.z_used, {"A"})
        self.assertTrue(holder.z_activated)
        self.assertEqual(holder.to_dict()["moves"][0]["pp"], 34)
        self.assertLess(foe.hp, foe.max_hp)
        self.assertEqual(self.player.trainer.get_item_quantity("Normalium Z"), 0)
        self.rebuild()
        self.assertEqual(self.session.battle.z_used, {"A"})
        self.session.end()
        self.record("hold", "3=")
        self.assertEqual(self.player.trainer.get_item_quantity("Normalium Z"), 1)

    def test_plain_attack_with_crystal_is_not_inferred_as_z(self):
        """A held crystal never turns an old/ordinary MOVE into a Z action."""
        self.equip()
        self.launch()
        self.resolve(z=False)
        self.assertFalse(self.session.battle.z_used)
        self.assertFalse(
            getattr(self.session.battle.participants[0].active[0], "z_activated", False)
        )

    def test_paid_history_requires_matching_proof_and_legacy_absence_stays_absent(self):
        """A historical move is restored only when both identity and use agree."""
        from pokemon.battle.logic import BattleLogic

        self.equip()
        self.launch()
        self.resolve()
        saved=self.session.logic.to_dict()
        # Locate actors by actual production snapshot shape, not a mutable ref.
        def actors(value):
            if isinstance(value,dict):
                if value.get("model_id") == "owned:"+str(self.mon.pk) and "moves" in value:
                    yield value
                for child in value.values():
                    yield from actors(child)
            elif isinstance(value,list):
                for child in value:
                    yield from actors(child)
        absent=deepcopy(saved)
        for actor in actors(absent):
            actor.pop("last_move",None)
        restored=BattleLogic.from_dict(absent)
        self.assertIsNone(restored.battle.participants[0].active[0].last_move)
        legacy=deepcopy(saved)
        for actor in actors(legacy):
            actor["last_move"].pop("z_source",None)
            actor["last_move"].pop("z_crystal",None)
        restored=BattleLogic.from_dict(legacy)
        self.assertEqual(restored.battle.participants[0].active[0].last_move._pp_move_name,"Tackle")
        self.assertTrue(restored.battle.participants[0].active[0].last_move._z_paid)
        forged=deepcopy(saved)
        found=False
        for actor in actors(forged):
            actor["last_move"]["z_source"]="Ember"
            found=True
        self.assertTrue(found)
        with self.assertRaises(ValueError):
            BattleLogic.from_dict(forged)
        orphan=deepcopy(saved)
        for actor in actors(orphan):
            actor["z_profile"]=None
            actor["z_activated"]=False
        with self.assertRaises(ValueError):
            BattleLogic.from_dict(orphan)

    def test_sleep_prevention_keeps_source_pp_and_side_unused(self):
        """The ordinary source prevention pass precedes the Z payment boundary."""
        core.OwnedPokemon.objects.filter(pk=self.mon.pk).update(status="slp", sleep_turns=3)
        core.OwnedPokemon.flush_cached_instance(self.mon)
        self.equip()
        self.launch()
        self.resolve()
        holder = self.session.battle.participants[0].active[0]
        self.assertFalse(self.session.battle.z_used)
        self.assertFalse(self.session.battle.z_pending)
        self.assertEqual(holder.to_dict()["moves"][0]["pp"], 35)

    def test_invalid_source_target_and_duplicate_input_queue_nothing_extra(self):
        """Unsupported pairs, stale labels and no-overwrite leave resources alone."""
        self.mon = self.fixture_native("Eevee", ["Tackle", "Tail Whip"], 3)
        self.equip()
        self.launch()
        for args in ("Tail Whip=B1", "3=B1", "Tackle=A9", "Tack=B1", "0=B1"):
            before = self.observation()
            self.record("zmove", args)
            self.assertEqual(self.observation(), before)
        with patch.object(self.session, "maybe_run_turn"):
            self.record("zmove", "1=B1")
            before = self.observation()
            self.record("zmove", "1=B1")
            self.record("attack", "Tackle B1")
            self.assertEqual(self.observation(), before)

    def queued(self):
        """Queue both real player actions while retaining the transaction boundary."""
        with patch.object(self.session, "maybe_run_turn"):
            self.record("zmove", "Tackle=B1")
            self.record("attack", "Growl A1", side=1)
        self.assertIn("A", self.session.battle.z_pending)

    def test_checkpoint_and_post_payment_faults_restore_exact_retry(self):
        """SQL PP, runtime, input, RNG and success output roll back together."""
        from pokemon.battle.z_moves import ZMoves

        self.equip()
        self.launch()
        self.queued()
        for fault in ("payment", "checkpoint"):
            before = self.observation()
            rng = self.session.battle.rng.getstate()
            start = len(self.player.messages)
            original_begin = ZMoves.begin.__func__
            original_set = self.session.storage.set

            def begin(cls, *args):
                """Fail after the real owned PP and budget payment."""
                original_begin(cls, *args)
                raise RuntimeError("Z payment fixture")

            def save(key, value):
                """Fail after effects and owned synchronization."""
                if key == "data":
                    raise RuntimeError("Z checkpoint fixture")
                return original_set(key, value)

            target = (
                patch.object(ZMoves, "begin", classmethod(begin))
                if fault == "payment"
                else patch.object(self.session.storage, "set", side_effect=save)
            )
            with target, self.assertRaisesRegex(RuntimeError, "Z .* fixture"):
                self.session.execute_persistent_turn()
            self.assertEqual(self.observation(), before)
            self.assertEqual(self.session.battle.rng.getstate(), rng)
            self.assertFalse(any("unleashed" in str(m) for m in self.player.messages[start:]))
        self.session.execute_persistent_turn()
        self.assertEqual(self.session.battle.z_used, {"A"})

    def test_queue_write_failure_has_no_action_reservation_or_notice(self):
        """Failure after a real Attribute write leaves no partial queued MOVE."""
        self.equip()
        self.launch()
        before, start = self.observation(), len(self.player.messages)
        original = self.session.storage.set

        def fail(key, value):
            """Raise after the real persisted declaration."""
            original(key, value)
            raise RuntimeError("Z declaration fixture")

        with patch.object(self.session.storage, "set", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "Z declaration fixture"):
                self.record("zmove", "Tackle=B1")
        self.assertEqual(self.observation(), before)
        self.assertFalse(any("prepares" in str(m) for m in self.player.messages[start:]))

    def test_last_pp_in_gapped_actual_slot_is_paid_once_under_pressure(self):
        """Numeric selection follows SQL slot four and never list index four."""
        from pokemon.models.moves import ActiveMoveslot, MovesetSlot

        ActiveMoveslot.objects.filter(pokemon=self.mon, slot=1).update(slot=4, current_pp=1)
        MovesetSlot.objects.filter(moveset=self.mon.active_moveset, slot=1).update(slot=4)
        core.OwnedPokemon.objects.filter(pk=self.foe.pk).update(ability="Pressure")
        core.OwnedPokemon.flush_cached_instance(self.foe)
        self.equip()
        self.launch()
        with patch.object(self.session, "maybe_run_turn"):
            self.record("zmove", "4=B1")
            self.record("attack", "Growl A1", side=1)
        self.rebuild()
        self.session.execute_persistent_turn()
        self.assertEqual(ActiveMoveslot.objects.get(pokemon=self.mon, slot=4).current_pp, 0)
        self.assertEqual(self.session.battle.z_used, {"A"})

    def test_stale_source_and_held_rows_abort_before_any_turn_commit(self):
        """Fresh SQL cannot be overwritten by a stale runtime held/PP mirror."""
        from pokemon.models.moves import ActiveMoveslot

        self.equip()
        self.launch()
        self.queued()
        slot = ActiveMoveslot.objects.get(pokemon=self.mon, slot=1)
        for model, pk, field, value, restore in (
            (ActiveMoveslot, slot.pk, "current_pp", 0, slot.current_pp),
            (core.OwnedPokemon, self.mon.pk, "held_item", "", "Normalium Z"),
            (
                core.OwnedPokemon,
                self.mon.pk,
                "trainer_id",
                self.players[1].trainer.pk,
                self.player.trainer.pk,
            ),
        ):
            model.objects.filter(pk=pk).update(**{field: value})
            before = self.observation()
            with self.assertRaises(ValueError):
                self.session.execute_persistent_turn()
            self.assertEqual(self.observation(), before)
            model.objects.filter(pk=pk).update(**{field: restore})
        self.session.execute_persistent_turn()
        self.assertEqual(self.session.battle.z_used, {"A"})

    def test_corrupt_proof_and_ledger_cannot_rebuild_or_refund(self):
        """Missing/changed Z identity fails closed instead of becoming ordinary."""
        from pokemon.battle.logic import BattleLogic

        self.equip()
        self.launch()
        self.queued()
        saved = self.session.logic.to_dict()
        for key, value in (
            ("version", 2),
            ("source_id", 0),
            ("profile", "changed"),
            ("controller", "999999"),
            ("turn", -1),
        ):
            damaged = deepcopy(saved)
            damaged["state"]["z_pending"]["A"][key] = value
            with self.assertRaises(ValueError):
                BattleLogic.from_dict(damaged)
        self.session.execute_persistent_turn()
        saved = self.session.logic.to_dict()
        damaged = deepcopy(saved)
        damaged["state"]["z_used"] = []
        with self.assertRaises(ValueError):
            BattleLogic.from_dict(damaged)
        self.rebuild()
        before = self.observation()
        self.record("zmove", "Tackle=B1")
        self.assertEqual(self.observation(), before)

    def test_doubles_side_contention_and_independent_opponent_payment(self):
        """A1/A2 share a budget; B1 retains its separate one-use budget."""
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections

        self.equip()
        for side, slot in ((0, 4), (1, 1)):
            self.players[side].trainer.add_item("Normalium Z")
            self.record("hold", f"{slot}=Normalium Z", side=side)
        self.launch("double")
        barrier = Barrier(2)

        def reserve(actor):
            """Race fresh SQL connections at the real room declaration lock."""
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    self.session.choices_for(self.player).zmove("Tackle", "B1", actor=actor)
                    return True
                except ValueError:
                    return False
            finally:
                close_old_connections()

        with (
            patch.object(self.session, "maybe_run_turn"),
            ThreadPoolExecutor(max_workers=2) as pool,
        ):
            self.assertEqual(sum(pool.map(reserve, ["A1", "A2"])), 1)
        winner = self.session.battle.z_pending["A"]["slot"]
        with patch.object(self.session, "maybe_run_turn"):
            self.record("attack", ("A2" if winner == "0" else "A1") + " Growl B1")
            self.record("zmove", "B1 Tackle=A1", side=1)
            self.record("attack", "B2 Growl A1", side=1)
        self.rebuild()
        self.session.execute_persistent_turn()
        self.assertEqual(self.session.battle.z_used, {"A", "B"})

    def test_protection_and_immunity_pay_one_pp_without_source_effects(self):
        """Personal Protect quarters damage; Ghost immunity still spends the use."""
        for protected, species in ((False, "Eevee"), (True, "Eevee"), (False, "Gastly")):
            if self.session:
                self.session.end()
                self.session = None
            self.foe = self.fixture_native(species, ["Protect", "Splash"], 1, side=1, level=100)
            if not core.OwnedPokemon.objects.get(pk=self.mon.pk).held_item:
                self.equip()
            self.launch()
            foe = self.session.battle.participants[1].active[0]
            hp = foe.hp
            with patch.object(self.session, "maybe_run_turn"):
                self.record("zmove", "Tackle=B1")
                self.record("attack", ("Protect B1" if protected else "Splash B1"), side=1)
            self.session.execute_persistent_turn()
            damage = hp - foe.hp
            if species == "Gastly":
                self.assertEqual(damage, 0)
            elif protected:
                self.assertEqual(damage, max(1, baseline // 4))
            else:
                baseline = damage
                self.assertGreater(baseline, 4)
            self.assertEqual(self.session.battle.z_used, {"A"})

    def test_failed_end_keeps_spent_use_and_next_battle_is_fresh(self):
        """Ending retry never reopens the side budget or consumes the crystal."""
        self.equip()
        self.launch()
        self.resolve()
        with patch.object(
            self.session, "_sync_player_pokemon_state", side_effect=RuntimeError("Z end fixture")
        ):
            with self.assertRaisesRegex(RuntimeError, "Z end fixture"):
                self.session.end()
        self.assertEqual(self.session.battle.z_used, {"A"})
        self.session.end()
        self.launch()
        self.assertFalse(self.session.battle.z_used)

    def negative(self, variant):
        """Fresh source/current actor rules reject before queuing or spending."""
        self.equip()
        self.launch()
        holder = self.session.battle.participants[0].active[0]
        field, old = None, None
        if variant in {"transformed", "fainted", "runtime_item", "native_spoof"}:
            field, value = {
                "transformed": ("transformed", True),
                "fainted": ("hp", 0),
                "runtime_item": ("item", None),
                "native_spoof": ("native_origin", {"ref": holder.model_id, "species": "Eevee"}),
            }[variant]
            old = getattr(holder, field, None)
            setattr(holder, field, value)
        elif variant == "disabled":
            holder.volatiles["disable"] = {"move": "tackle", "duration": 4}
        elif variant == "egg":
            core.OwnedPokemon.objects.filter(pk=self.mon.pk).update(is_egg=True)
        elif variant == "tera_pending":
            self.session.battle.tera_pending["A"] = {"pokemon": str(holder.model_id)}
        elif variant == "mega_pending":
            self.session.battle.mega_pending["A"] = {"pokemon": str(holder.model_id)}
        if variant in {"mega_pending", "tera_pending"}:
            self.session.logic.sync_runtime_state()
            self.session._persist_turn_state()
        before = self.observation()
        self.record("zmove", "Tackle=B1")
        self.assertEqual(self.observation(), before)
        self.assertFalse(self.session.battle.z_pending)
        if field:
            setattr(holder, field, old)
        core.OwnedPokemon.objects.filter(pk=self.mon.pk).update(is_egg=False)
        self.session.battle.tera_pending = {}
        self.session.battle.mega_pending = {}

    def test_switch_faint_revive_benched_rebuild_keeps_spent_budget(self):
        """Only a new session resets use, including manual revival of a spent holder."""
        self.equip()
        self.launch()
        self.resolve()
        holder = self.session.battle.participants[0].active[0]
        holder.hp, holder.is_fainted = 0, True
        self.session.battle.run_faint()
        self.session._sync_player_pokemon_state(strict=True)
        self.session._sync_active_battle_state()
        self.player.trainer.add_item("Revive")
        with patch.object(self.session, "maybe_run_turn"):
            self.record("item", "Revive=3")
            self.record("attack", "Growl A1", side=1)
        self.session.execute_persistent_turn()
        self.assertGreater(holder.hp, 0)
        self.rebuild()
        self.assertEqual(self.session.battle.z_used, {"A"})
        with patch.object(self.session, "maybe_run_turn"):
            self.record("switch", "3")
            self.record("attack", "Growl A1", side=1)
        self.session.execute_persistent_turn()
        self.assertTrue(self.session.battle.participants[0].active[0].z_activated)
        self.assertEqual(self.session.battle.z_used, {"A"})

    def test_distinct_allies_can_use_z_mega_and_tera_without_stacking(self):
        """Different actors have independent mechanic budgets; held Z prevents Tera."""
        self.equip()
        self.player.trainer.add_item("Venusaurite")
        ally = self.fixture_native("Venusaur", ["Tackle", "Growl"], 4)
        self.record("hold", "4=Venusaurite")
        self.launch("double")
        before = self.observation()
        self.record("tera", "A1")
        self.record("mega", "A1")
        self.assertEqual(self.observation(), before)
        with patch.object(self.session, "maybe_run_turn"):
            self.record("zmove", "A1 Tackle=B1")
            self.record("mega", "A2")
            self.record("attack", "A2 Tackle B1")
            self.record("attack", "B1 Growl A1", side=1)
            self.record("attack", "B2 Growl A1", side=1)
        self.session.execute_persistent_turn()
        self.assertEqual(self.session.battle.z_used, {"A"})
        self.assertEqual(self.session.battle.mega_used, {"A"})
        self.session.end()
        self.session = None
        self.record("hold", "4=")
        self.launch("double")
        with patch.object(self.session, "maybe_run_turn"):
            self.record("tera", "A2")
            self.record("zmove", "A1 Tackle=B1")
            self.record("attack", "A2 Growl B1")
            self.record("attack", "B1 Growl A1", side=1)
            self.record("attack", "B2 Growl A1", side=1)
        self.session.execute_persistent_turn()
        self.assertEqual(self.session.battle.z_used, {"A"})
        self.assertEqual(self.session.battle.tera_used, {"A"})

    def test_first_effect_has_exact_power_noncontact_and_accuracy_bypass(self):
        """Actual Z damage exceeds ordinary Tackle without Rough Skin contact cost."""
        damages = []
        for z in (False, True):
            if self.session:
                self.session.end()
                self.session = None
            self.mon = self.fixture_native("Eevee", ["Tackle", "Growl"], 3)
            self.foe = self.fixture_native("Eevee", ["Splash"], 1, side=1, level=100)
            core.OwnedPokemon.objects.filter(pk=self.foe.pk).update(ability="Rough Skin")
            core.OwnedPokemon.flush_cached_instance(self.foe)
            # Separate setup of a fresh copy; the actual normal input equips it.
            self.player.trainer.add_item("Normalium Z")
            self.record("hold", "3=Normalium Z")
            self.launch()
            battle = self.session.battle
            holder, foe = (part.active[0] for part in battle.participants)
            hp, foe_hp = holder.hp, foe.hp
            with patch.object(self.session, "maybe_run_turn"):
                self.record("zmove" if z else "attack", "Tackle=B1" if z else "Tackle B1")
                self.record("attack", "Splash B1", side=1)
            self.session.execute_persistent_turn()
            damages.append(foe_hp - foe.hp)
            self.assertEqual(holder.hp == hp, z)
        self.assertGreater(damages[1], damages[0] * 2)
        from pokemon.battle.z_profiles import ZProfiles

        descriptor = ZProfiles.get("Normalium Z", "Tackle").descriptor(holder.moves[0])
        self.assertEqual(
            (
                descriptor.power,
                descriptor.category,
                descriptor.type,
                descriptor.priority,
                descriptor.accuracy,
            ),
            (100, "Physical", "Normal", 0, True),
        )
        self.assertFalse(descriptor.raw["flags"].get("contact"))
        self.assertFalse(battle.run_called_move(holder, descriptor, foe))
        self.assertFalse(battle.run_called_move(holder, "Breakneck Blitz", foe))

    def suppression(self, variant):
        """Actual matching crystal ownership survives held-effect suppression."""
        self.equip()
        self.launch()
        holder = self.session.battle.participants[0].active[0]
        if variant == "klutz":
            holder.setAbility("Klutz", battle=self.session.battle)
        elif variant == "embargo":
            holder.volatiles["embargo"] = {"duration": 5}
        elif variant == "magicroom":
            self.session.battle.field.pseudo_weather["magicroom"] = {"duration": 5}
        else:
            holder.item_suppressed = True
        self.resolve()
        self.assertEqual(self.session.battle.z_used, {"A"})
        self.assertEqual(core.OwnedPokemon.objects.get(pk=self.mon.pk).held_item, "Normalium Z")

    def battle_kind(self, kind):
        """Ordinary human input works in current Fusion, Wild and Trainer sessions."""
        self.equip()
        if kind == "fusion":
            core.PlacementService(self.player.storage).reserve_for_fusion(self.mon)
            self.player.db.fusion_id, self.player.db.fusion_kind = str(self.mon.pk), "full"
            self.player.db.fusion_species, self.player.db.morphology = "Venusaur", "Human"
            self.player.db.total_exp, self.player.db.trainer_xp = self.mon.total_exp, 1000
            self.player.db.fusion_battle_order = "first"
            self.launch()
            self.resolve(rebuild=True)
        else:
            self.launch(kind=kind)
            self.record("zmove", "Tackle=B1")
            self.assertFalse(self.session.turn_state.get("error"), self.session.turn_state)
        self.assertEqual(self.session.battle.z_used, {"A"})

    def test_opt_in_counter_install_purchase_no_refill_and_return_exit(self):
        """Install only in a tagged private hub and use its real finite Buy menu."""
        from types import SimpleNamespace
        from evennia.utils.create import create_object
        from pokemon.services.item_counter import ItemCounter

        hub = create_object("typeclasses.rooms.FusionRoom", key="private Z hub", nohome=True)
        counter = ItemCounter("world/z_crystal_counter.json")
        room = counter.install(hub)
        receipt = hub.attributes.get("counter_z-crystal-counter-v1")
        self.installed_objects.extend(
            [hub.pk, *[receipt[key] for key in ("room", "entrance", "return_exit")]]
        )
        self.assertEqual(counter.install(hub).pk, room.pk)
        self.room = SimpleNamespace(
            id=room.pk,
            pk=room.pk,
            key=room.key,
            db=room.db,
            ndb=room.ndb,
            attributes=room.attributes,
            contents=self.players,
        )
        for player in self.players:
            player.location = self.room
        before = self.state()
        self.command("store")
        for text in ("1", "Normalium Z 1", "back", "q"):
            self.reply(text)
        self.assertEqual(self.state()["wallet"], before["wallet"] - 10000)
        self.assertEqual(self.state()["stock"]["Normalium Z"]["quantity"], 0)
        self.assertEqual(counter.install(hub).pk, room.pk)
        self.assertEqual(self.state()["stock"]["Normalium Z"]["quantity"], 0)
        self.record("inventory")
        self.record("hold", "3=Normalium Z")
        self.launch()
        self.resolve(rebuild=True)
        self.session.end()
        self.record("hold", "3=")
        self.assertEqual(self.player.trainer.get_item_quantity("Normalium Z"), 1)
        for key, origin, destination in (("entrance", hub, room), ("return_exit", room, hub)):
            exit_row = core.acquisition.ObjectDB.objects.get(pk=receipt[key])
            self.assertEqual(
                (exit_row.db_location_id, exit_row.db_destination_id), (origin.pk, destination.pk)
            )
            character=self.player.character
            character.move_to(origin,quiet=True,move_hooks=False)
            traversal=exit_row.exit_command()
            traversal.caller,traversal.obj=character,exit_row
            traversal.func()
            character.refresh_from_db()
            self.assertEqual(character.db_location_id,destination.pk)
            core.EVIDENCE.append({"case":self._testMethodName,"event":"actual-counter-exit-command",
                                  "command":exit_row.key,"origin":origin.pk,"destination":destination.pk,
                                  "saved_player_location":character.db_location_id})

    def test_native_pixilate_player_keeps_normal_z_immunity_and_pays_source(self):
        """An actual native hidden ability cannot convert a paid Normalium action."""
        self.mon = self.fixture_native("Sylveon", ["Tackle", "Growl"], 3)
        self.foe = self.fixture_native("Gastly", ["Splash"], 1, side=1, level=100)
        core.OwnedPokemon.objects.filter(pk=self.mon.pk).update(ability="Pixilate")
        core.OwnedPokemon.flush_cached_instance(self.mon)
        self.equip()
        self.launch()
        holder, foe = (part.active[0] for part in self.session.battle.participants)
        hp = foe.hp
        with patch.object(self.session, "maybe_run_turn"):
            self.record("zmove", "Tackle=B1")
            self.record("attack", "Splash B1", side=1)
        self.session.execute_persistent_turn()
        self.assertEqual(foe.hp, hp)
        self.assertEqual(self.session.battle.z_used, {"A"})
        from pokemon.models.moves import ActiveMoveslot

        self.assertEqual(ActiveMoveslot.objects.get(pokemon=self.mon, slot=1).current_pp, 34)
        with patch.object(self.session, "maybe_run_turn"):
            self.record("attack", "Tackle B1")
            self.record("attack", "Splash B1", side=1)
        self.session.execute_persistent_turn()
        self.assertLess(foe.hp, hp)

    def test_fainted_before_z_acts_spends_no_pp_or_side_use(self):
        """A real faster priority KO prevents activation rather than paying it."""
        from pokemon.models.moves import ActiveMoveslot

        core.OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=1)
        core.OwnedPokemon.flush_cached_instance(self.mon)
        self.foe = self.fixture_native("Mew", ["Quick Attack"], 1, side=1, level=100)
        self.equip()
        self.launch()
        with patch.object(self.session, "maybe_run_turn"):
            self.record("zmove", "Tackle=B1")
            self.record("attack", "Quick Attack A1", side=1)
        self.session.execute_persistent_turn()
        self.assertFalse(self.session.battle.z_used)
        self.assertEqual(ActiveMoveslot.objects.get(pokemon=self.mon, slot=1).current_pp, 35)
        self.rebuild()
        self.assertFalse(self.session.battle.z_used)

    def test_legal_target_switch_follows_slot_without_an_ordinary_fallback(self):
        """Pre-switch binding permits the actual chosen slot's legal replacement."""
        self.equip()
        self.launch()
        original = self.session.battle.participants[1].active[0]
        with patch.object(self.session, "maybe_run_turn"):
            self.record("zmove", "Tackle=B1")
            self.record("switch", "2", side=1)
        self.session.execute_persistent_turn()
        target = self.session.battle.participants[1].active[0]
        self.assertIsNot(target, original)
        self.assertLess(target.hp, target.max_hp)
        self.assertEqual(original.hp, original.max_hp)
        self.assertEqual(self.session.battle.z_used, {"A"})

    def test_real_faster_spite_can_prevent_z_without_rolling_back_its_turn(self):
        """Legitimate in-turn PP depletion commits and leaves the Z budget unused."""
        from pokemon.models.moves import ActiveMoveslot

        ActiveMoveslot.objects.filter(pokemon=self.mon, slot=1).update(current_pp=5)
        self.foe = self.fixture_native("Mew", ["Splash", "Spite"], 1, side=1, level=100)
        self.equip()
        self.launch()
        with patch.object(self.session, "maybe_run_turn"):
            self.record("attack", "Tackle B1")
            self.record("attack", "Splash B1", side=1)
        self.session.execute_persistent_turn()
        self.assertEqual(ActiveMoveslot.objects.get(pokemon=self.mon, slot=1).current_pp, 4)
        with patch.object(self.session, "maybe_run_turn"):
            self.record("zmove", "Tackle=B1")
            self.record("attack", "Spite A1", side=1)
        self.session.execute_persistent_turn()
        self.assertEqual(ActiveMoveslot.objects.get(pokemon=self.mon, slot=1).current_pp, 0)
        self.assertFalse(self.session.battle.z_used)


    def test_spite_after_z_rebuild_drains_the_original_source_pp(self):
        """A reconstructed Z history keeps its underlying Tackle PP ownership."""
        from pokemon.models.moves import ActiveMoveslot

        self.foe = self.fixture_native("Mew", ["Splash", "Spite"], 1, side=1, level=100)
        self.equip()
        self.launch()
        with patch.object(self.session,"maybe_run_turn"):
            self.record("zmove","Tackle=B1")
            self.record("attack","Splash B1",side=1)
        self.session.execute_persistent_turn()
        self.assertEqual(ActiveMoveslot.objects.get(pokemon=self.mon,slot=1).current_pp,34)
        self.rebuild()
        with patch.object(self.session,"maybe_run_turn"):
            self.record("attack","Growl B1")
            self.record("attack","Spite A1",side=1)
        self.session.execute_persistent_turn()
        self.assertEqual(ActiveMoveslot.objects.get(pokemon=self.mon,slot=1).current_pp,30)
        self.assertEqual(self.session.battle.z_used,{"A"})


for _variant in (
    "transformed",
    "fainted",
    "runtime_item",
    "native_spoof",
    "disabled",
    "egg",
    "tera_pending",
    "mega_pending",
):

    def _case(self, variant=_variant):
        """One isolated rejection control with actual player input."""
        self.negative(variant)

    setattr(ZMoveCases, "test_reject_" + _variant, _case)

for _method, _variants in (
    ("suppression", ("klutz", "embargo", "magicroom", "flag")),
    ("battle_kind", ("wild", "trainer", "fusion")),
):
    for _variant in _variants:

        def _case(self, method=_method, variant=_variant):
            """Exercise a distinct production route in its own private fixture."""
            getattr(self, method)(variant)

        setattr(ZMoveCases, "test_" + _method + "_" + _variant, _case)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        core.load_runtime()
        import evennia
        from evennia.commands.command import Command
        from evennia.commands.cmdset import CmdSet

        with patch.object(evennia, "Command", Command), patch.object(evennia, "CmdSet", CmdSet):
            from commands.player import cmd_battle_zmove
        core.acquisition.COMMANDS["zmove"] = cmd_battle_zmove, cmd_battle_zmove.CmdBattleZMove
        try:
            result = unittest.TextTestRunner(verbosity=2).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(ZMoveCases)
            )
        finally:
            if os.environ.get("PF2_Z_EVIDENCE"):
                Path(os.environ["PF2_Z_EVIDENCE"]).write_text(
                    json.dumps(core.EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8"
                )
        raise SystemExit(not result.wasSuccessful())

"""Ordinary Ultra preview/attack/Z inputs with genuine captured native pairs."""

from copy import deepcopy
import importlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import ultra_preparation_cases as preparation
import necrozma_player_cases as native


class UltraBattleCases(preparation.UltraPreparationCases):
    """Keep setup, actual commands, SQL and runtime observations separately."""

    def setUp(self):
        """Expose real SQL room Attributes on the captured transport facade."""
        super().setUp()
        from evennia.objects.models import ObjectDB

        self.room.db_attributes = ObjectDB.objects.get(pk=self.room.pk).db_attributes

    def egg_roster_flow(self, companion):
        """Keep a genuine owned egg outside the roster during both Ultra guarded turns."""
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.services.placement import PlacementService

        launch = self.launch
        eggs = []

        def launch_with_egg(battle_format="single"):
            """Separate an unhatched egg prerequisite from normal player startup."""
            egg = create_owned_pokemon(
                "Eevee", self.player.trainer, 1, nature="Hardy", ability="Run Away",
                ivs=[0] * 6, evs=[0] * 6, active_move_names=["Tackle"],
            )
            egg.is_egg = True
            egg.save(update_fields=("is_egg",))
            PlacementService(self.player.storage).to_party(egg, slot=1)
            eggs.append(OwnedPokemon.objects.filter(pk=egg.pk).values().get())
            native.core.EVIDENCE.append(dict(
                event="separate-unhatched-party-egg-prerequisite", row=eggs[-1],
            ))
            launch(battle_format)
            self.assertNotIn("owned:" + str(egg.pk), [mon.model_id for part in
                             self.session.battle.participants for mon in part.pokemons])

        self.launch = launch_with_egg
        self.activate(companion)
        self.attacks(signature=True)
        self.rebuild()
        self.refresh_actor()
        self.assertEqual(self.actor.species, "Necrozma-Ultra")
        self.assertEqual(OwnedPokemon.objects.filter(pk=eggs[0]["unique_id"]).values().get(), eggs[0])
        self.assertFalse(self.session.turn_state.get("error"), self.session.turn_state)
        self.assertFalse(getattr(self.session.battle, "_callback_failures", []))
        native.core.EVIDENCE.append(dict(
            event="accepted-ultra-signature-with-excluded-party-egg", companion=companion,
            egg_before=eggs[0], egg_after=OwnedPokemon.objects.filter(pk=eggs[0]["unique_id"]).values().get(),
            after=self.observation(),
        ))

    def test_dawn_ultra_guarded_turns_exclude_party_egg(self):
        """Dawn Ultra activation and its signature leave the real party egg untouched."""
        self.egg_roster_flow("Lunala")

    def test_dusk_ultra_guarded_turns_exclude_party_egg(self):
        """Dusk uses the same repaired roster and persistent whole-turn guards."""
        self.egg_roster_flow("Solgaleo")

    def refresh_actor(self):
        """Follow the current restored engine instead of retaining stale adapters."""
        self.participant = self.session.battle.participants[0]
        self.actor = next(
            mon for mon in self.participant.pokemons if mon.model_id == "owned:" + str(self.host.pk)
        )

    def preview(self, args=""):
        """Drive the production generator's ordinary yes/no transport explicitly."""
        from commands.player import cmd_battle_ultra

        before = self.observation()
        command = cmd_battle_ultra.CmdBattleUltra()
        command.caller, command.args, command.cmdstring = self.player, args, "+ultra"
        command.parse()
        with patch.object(
            cmd_battle_ultra, "get_system", return_value=SimpleNamespace(battle_manager=None)
        ):
            generator = command.func()
            try:
                prompt = next(generator)
            except StopIteration:
                native.core.EVIDENCE.append(
                    dict(
                        case=self._testMethodName,
                        command="+ultra " + args,
                        before=before,
                        after=self.observation(),
                        messages=list(map(str, self.player.messages[-3:])),
                    )
                )
                return None
        self.player.msg(prompt)
        self.assertEqual(self.observation(), before)
        native.core.EVIDENCE.append(
            dict(
                case=self._testMethodName,
                command="+ultra " + args,
                prompt=prompt,
                before=before,
                after=self.observation(),
                transport="captured ordinary generator",
            )
        )
        self.preview_generator = generator
        return prompt

    def answer(self, answer):
        """Deliver one ordinary answer and retain independently reloaded state."""
        from commands.player import cmd_battle_ultra

        before, start = self.observation(), len(self.player.messages)
        with patch.object(
            cmd_battle_ultra, "get_system", return_value=SimpleNamespace(battle_manager=None)
        ):
            with self.assertRaises(StopIteration):
                self.preview_generator.send(answer)
        native.core.EVIDENCE.append(
            dict(
                case=self._testMethodName,
                input=answer,
                before=before,
                after=self.observation(),
                messages=list(map(str, self.player.messages[start:])),
            )
        )

    def attacks(self, *, signature=False):
        """Queue real attacks and execute exactly one whole persisted turn."""
        from pokemon.battle.legal_actions import LegalActions

        with patch.object(self.session, "maybe_run_turn"):
            if signature:
                self.record("zmove", "Photon Geyser=B1")
            else:
                self.refresh_actor()
                actions = LegalActions(self.session.battle, self.participant, self.actor).moves()
                selected = next(
                    action
                    for action in actions
                    if normalize_name(action.move.name) != "photongeyser"
                )
                self.record("attack", selected.move.key + " B1")
            self.record("attack", "Growl A1", side=1)
        self.assertEqual(set(self.session.state.declare), {"A1", "B1"}, self.player.messages[-8:])
        self.session.execute_persistent_turn()
        self.refresh_actor()

    def activate(self, companion="Solgaleo", *, photon_pp=None):
        """Actual source preparation, reviewed yes, then a normal attack."""
        self.prepare(companion, photon_pp=photon_pp)
        source = ActiveMoveslot.objects.get(pokemon=self.host, slot=1)
        pp = source.current_pp
        self.assertIn("Confirm", self.preview())
        self.answer("yes")
        self.assertFalse(self.session.state.declare)
        self.assertTrue(self.session.battle.ultra_pending)
        self.rebuild()
        self.refresh_actor()
        self.attacks()
        self.assertEqual(self.actor.species, "Necrozma-Ultra")
        self.assertEqual(self.actor.types, ["Psychic", "Dragon"])
        self.assertEqual(
            normalize_name(getattr(self.actor.ability, "name", self.actor.ability)), "neuroforce"
        )
        self.assertEqual(self.session.battle.ultra_used, {"A"})
        self.assertFalse(self.session.battle.z_used)
        self.assertEqual(ActiveMoveslot.objects.get(pokemon=self.host, slot=1).current_pp, pp)
        self.assertEqual(
            OwnedPokemon.objects.get(pk=self.host.pk).species,
            "Necrozma-Dusk-Mane" if companion == "Solgaleo" else "Necrozma-Dawn-Wings",
        )
        self.assertEqual(
            OwnedPokemon.objects.filter(pk=self.companion.pk).values().get(), self.partner_before
        )

    def full_flow(self, companion):
        """Both forms activate, reconnect, spend one Photon/Z and separate safely."""
        self.activate(companion)
        self.rebuild()
        self.refresh_actor()
        self.assertEqual(self.actor.species, "Necrozma-Ultra")
        before = ActiveMoveslot.objects.get(pokemon=self.host, slot=1).current_pp
        target_hp = self.session.battle.participants[1].active[0].hp
        self.attacks(signature=True)
        self.assertEqual(self.session.battle.z_used, {"A"})
        self.assertEqual(
            ActiveMoveslot.objects.get(pokemon=self.host, slot=1).current_pp, before - 1
        )
        self.assertIn("Light That Burns the Sky", "\n".join(map(str, self.player.messages)))
        self.assertLess(self.session.battle.participants[1].pokemons[0].hp, target_hp)
        self.rebuild()
        self.refresh_actor()
        self.assertEqual(self.actor.species, "Necrozma-Ultra")
        battle = self.session.battle
        self.session.end()
        self.session = None
        self.assertEqual(
            self.actor.species,
            "Necrozma-Dusk-Mane" if companion == "Solgaleo" else "Necrozma-Dawn-Wings",
        )
        self.assertEqual(battle.ultra_used, {"A"})
        self.record("hold", "3=")
        self.assertEqual(self.player.trainer.get_item_quantity("Ultranecrozium Z"), 1)
        self.separate()

    def test_dusk_complete_ordinary_ultra_signature_restore_and_separate(self):
        self.full_flow("Solgaleo")

    def test_dawn_complete_ordinary_ultra_signature_restore_and_separate(self):
        self.full_flow("Lunala")

    def test_declined_and_changed_terms_spend_nothing(self):
        self.prepare("Solgaleo")
        before = self.observation()
        self.preview()
        self.answer("no")
        self.assertEqual(self.observation(), before)
        self.preview()
        ActiveMoveslot.objects.filter(pokemon=self.host, slot=1).update(current_pp=0)
        self.answer("yes")
        self.assertFalse(self.session.battle.ultra_pending)
        self.assertFalse(self.session.state.declare)
        self.assertIn("terms changed", "\n".join(map(str, self.player.messages[-3:])))

    def test_zero_photon_can_activate_without_refilling_or_using_signature(self):
        self.activate("Lunala", photon_pp=0)
        before = self.observation()
        self.record("zmove", "Photon Geyser=B1")
        self.assertEqual(self.observation(), before)
        self.assertFalse(self.session.battle.z_used)

    def test_later_ability_replacement_survives_reconnect_and_signature(self):
        self.activate()
        self.actor.setAbility(
            "Synchronize",
            battle=self.session.battle,
            source=self.session.battle.participants[1].active[0],
        )
        self.rebuild()
        self.refresh_actor()
        self.assertEqual(
            normalize_name(getattr(self.actor.ability, "name", self.actor.ability)), "synchronize"
        )
        self.attacks(signature=True)
        self.assertEqual(
            normalize_name(getattr(self.actor.ability, "name", self.actor.ability)), "synchronize"
        )

    def test_checkpoint_failure_restores_declaration_form_budget_pp_rng_and_notice(self):
        self.prepare("Lunala")
        self.preview()
        self.answer("yes")
        with patch.object(self.session, "execute_persistent_turn") as run:
            self.attacks()
            self.assertEqual(run.call_count, 1)
        before, rng, start = (
            self.observation(),
            self.session.battle.rng.getstate(),
            len(self.player.messages),
        )
        original = self.session.storage.set

        def fail(key, value):
            """Inject after the actual transformation, attacks and SQL sync."""
            if key == "data":
                raise RuntimeError("Ultra checkpoint fixture")
            return original(key, value)

        with patch.object(self.session.storage, "set", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "Ultra checkpoint fixture"):
                self.session.execute_persistent_turn()
        self.assertEqual(self.observation(), before)
        self.assertEqual(self.session.battle.rng.getstate(), rng)
        self.assertFalse(
            any("used Ultra Burst" in str(message) for message in self.player.messages[start:])
        )
        self.session.execute_persistent_turn()
        self.refresh_actor()
        self.assertEqual(self.actor.species, "Necrozma-Ultra")
        self.assertEqual(self.session.battle.ultra_used, {"A"})

    def test_cancel_queued_ultra_keeps_the_ordinary_attack_and_budget(self):
        """Cancel only the unspent form declaration while the other side is waiting."""
        self.prepare("Solgaleo")
        self.preview()
        self.answer("yes")
        with patch.object(self.session, "maybe_run_turn"):
            self.record("attack", "Sunsteel Strike B1")
        queued = deepcopy(self.session.state.declare)
        self.assertIsNone(self.preview("cancel"))
        self.assertEqual(self.session.state.declare, queued)
        self.assertFalse(self.session.battle.ultra_pending)
        with patch.object(self.session, "maybe_run_turn"):
            self.record("attack", "Growl A1", side=1)
        self.session.execute_persistent_turn()
        self.refresh_actor()
        self.assertEqual(self.actor.species, "Necrozma-Dusk-Mane")
        self.assertFalse(self.session.battle.ultra_used)

    def test_normal_switch_cancels_pending_and_switch_save_failure_restores_it(self):
        """A cancelled declaration and the legal non-move share one saved boundary."""
        self.prepare("Lunala")
        self.preview()
        self.answer("yes")
        before = self.observation()
        with patch.object(
            self.session.storage, "set", side_effect=RuntimeError("switch checkpoint fixture")
        ):
            with self.assertRaisesRegex(RuntimeError, "switch checkpoint fixture"):
                self.session.choices_for(self.player).switch("4")
        self.assertEqual(self.observation(), before)
        with patch.object(self.session, "maybe_run_turn"):
            self.record("switch", "4")
            self.record("attack", "Growl A1", side=1)
        self.assertFalse(self.session.battle.ultra_pending)
        self.session.execute_persistent_turn()
        self.assertFalse(self.session.battle.ultra_used)

    def test_activation_retains_switch_form_and_resets_only_normal_entry_ability(self):
        """Ultra stays spent/present across ordinary switches; reentry gets Neuroforce."""
        self.activate()
        self.actor.setAbility(
            "Synchronize",
            battle=self.session.battle,
            source=self.session.battle.participants[1].active[0],
        )
        for slot in ("4", "3"):
            with patch.object(self.session, "maybe_run_turn"):
                self.record("switch", slot)
                self.record("attack", "Growl A1", side=1)
            self.session.execute_persistent_turn()
            self.rebuild()
        self.refresh_actor()
        self.assertIs(self.participant.active[0], self.actor)
        self.assertEqual(self.actor.species, "Necrozma-Ultra")
        self.assertEqual(
            normalize_name(getattr(self.actor.ability, "name", self.actor.ability)), "neuroforce"
        )
        self.assertEqual(self.session.battle.ultra_used, {"A"})

    def test_faint_revert_and_ordinary_revive_do_not_refund_or_reactivate(self):
        """A separately labelled HP0 condition uses actual faint and +item Revive."""
        self.activate("Lunala")
        self.actor.hp, self.actor.is_fainted = 0, False
        native.core.EVIDENCE.append(
            dict(case=self._testMethodName, fixture="labelled runtime HP0 before actual run_faint")
        )
        self.session.battle.run_faint()
        self.assertEqual(self.actor.species, "Necrozma-Dawn-Wings")
        self.assertFalse(self.actor.ultra_profile["active"])
        self.session._sync_player_pokemon_state(strict=True)
        self.session._sync_active_battle_state()
        self.session._persist_turn_state()
        self.buy("Revive", price=100, quantity=1)
        with patch.object(self.session, "maybe_run_turn"):
            self.record("item", "Revive=3")
            self.record("attack", "Growl A1", side=1)
        self.session.execute_persistent_turn()
        self.refresh_actor()
        self.assertGreater(self.actor.hp, 0)
        self.assertEqual(self.actor.species, "Necrozma-Dawn-Wings")
        self.assertEqual(self.session.battle.ultra_used, {"A"})
        self.rebuild()
        self.refresh_actor()
        with patch.object(self.session, "maybe_run_turn"):
            self.record("switch", "3")
            self.record("attack", "Growl A1", side=1)
        self.session.execute_persistent_turn()
        self.assertIsNone(self.preview())
        self.assertFalse(self.session.battle.ultra_pending)

    def test_confirmed_current_photon_pp_change_is_not_a_custody_fault(self):
        """Lawful PP changes after yes do not refill or discard the paid ordinary turn."""
        self.prepare("Solgaleo")
        self.preview()
        self.answer("yes")
        slot = ActiveMoveslot.objects.get(pokemon=self.host, slot=1)
        current = max(0, slot.current_pp - 1)
        ActiveMoveslot.objects.filter(pk=slot.pk).update(current_pp=current)
        next(
            move for move in self.actor.moves if normalize_name(move.name) == "photongeyser"
        ).pp = current
        native.core.EVIDENCE.append(
            dict(
                case=self._testMethodName,
                fixture="labelled intervening Photon resource change",
                current_pp=current,
            )
        )
        self.attacks()
        self.assertEqual(self.actor.species, "Necrozma-Ultra")
        self.assertEqual(ActiveMoveslot.objects.get(pk=slot.pk).current_pp, current)

    def test_outer_confirmation_and_turn_refuse_before_success_or_resource_change(self):
        """Containing transactions cannot leak declarations, forms, budgets or notices."""
        from django.db import transaction

        self.prepare("Solgaleo")
        self.preview()
        before = self.observation()
        with transaction.atomic():
            self.answer("yes")
        self.assertEqual(self.observation(), before)
        self.preview()
        self.answer("yes")
        with patch.object(self.session, "execute_persistent_turn"):
            self.attacks()
        before = self.observation()
        with transaction.atomic(), self.assertRaisesRegex(ValueError, "containing transaction"):
            self.session.execute_persistent_turn()
        self.assertEqual(self.observation(), before)

    def test_changed_native_ability_at_commit_aborts_whole_turn(self):
        """No silent ordinary fallback may spend an action after stale Ultra proof."""
        self.prepare("Lunala")
        self.preview()
        self.answer("yes")
        with patch.object(self.session, "execute_persistent_turn"):
            self.attacks()
        self.actor.setAbility(
            "Synchronize",
            battle=self.session.battle,
            source=self.session.battle.participants[1].active[0],
        )
        before = self.observation()
        with self.assertRaisesRegex(ValueError, "native Prism Armor"):
            self.session.execute_persistent_turn()
        self.assertEqual(self.observation(), before)
        self.assertFalse(self.session.battle.ultra_used)
        # Safe ordinary custody cleanup does not require a new activation grant.
        self.session.end()
        self.session = None
        self.separate()

    def test_doubles_require_owned_actor_and_keep_sibling_choice(self):
        """Ambiguous/wrong-side declarations do not overwrite another active choice."""
        self.prepare("Solgaleo", battle_format="double")
        before = self.observation()
        self.assertIsNone(self.preview())
        self.assertIsNone(self.preview("B1"))
        self.assertEqual(self.observation(), before)
        self.assertIn("Confirm", self.preview("A1"))
        self.answer("yes")
        with patch.object(self.session, "maybe_run_turn"):
            self.record("attack", "A2 Growl B1")
        sibling = deepcopy(self.session.state.declare["A2"])
        with patch.object(self.session, "maybe_run_turn"):
            self.record("attack", "A1 Sunsteel Strike B1")
            self.record("attack", "B1 Growl A1", side=1)
            self.record("attack", "B2 Growl A1", side=1)
        self.assertEqual(self.session.state.declare["A2"], sibling)
        self.session.execute_persistent_turn()
        self.refresh_actor()
        self.assertEqual(self.actor.species, "Necrozma-Ultra")

    def test_unbound_raw_ultra_and_spent_ledger_do_not_restore(self):
        """Neither a species string nor a free spent marker constitutes native proof."""
        from pokemon.battle.ultra_burst import UltraBurst

        self.prepare("Lunala")
        species = self.actor.species
        try:
            self.actor.species = "Necrozma-Ultra"
            with self.assertRaisesRegex(ValueError, "Unbound Ultra"):
                UltraBurst.recover(self.session.battle)
        finally:
            self.actor.species = species
        with patch.object(self.session.battle, "ultra_used", {"A"}):
            with self.assertRaisesRegex(ValueError, "spent ledger"):
                UltraBurst.recover(self.session.battle)

    def test_dormant_photon_cannot_be_activated_while_combined(self):
        """Legitimately learned knowledge does not substitute for an active source."""
        self.prepare("Solgaleo", active_photon=False)
        before = self.observation()
        self.assertIsNone(self.preview())
        self.assertEqual(self.observation(), before)
        self.assertFalse(self.session.battle.ultra_pending)

    def test_displaced_photon_must_be_prepared_before_a_new_combination(self):
        """A real selected temporary binding cannot share its displaced Photon slot."""
        self.prepare("Lunala", combine_slot=1)
        before = self.observation()
        self.assertIsNone(self.preview())
        self.assertEqual(self.observation(), before)
        self.assertFalse(self.session.battle.ultra_pending)
        self.session.end()
        self.session = None
        self.separate()
        self.assertEqual(
            normalize_name(ActiveMoveslot.objects.get(pokemon=self.host, slot=1).move.name),
            "photongeyser",
        )

    def test_foreign_appearance_and_physical_crystal_cannot_supply_native_proof(self):
        """Nickname, transformed appearance and human Fusion do not qualify."""
        self.prepare("Solgaleo")
        for attribute, value in (
            ("native_origin", {}),
            ("transformed", True),
            ("_pf2_active_fusion", True),
            ("item", None),
        ):
            existed = hasattr(self.actor, attribute)
            old = getattr(self.actor, attribute, None)
            try:
                setattr(self.actor, attribute, value)
                before = self.observation()
                self.assertIsNone(self.preview())
                self.assertEqual(self.observation(), before)
            finally:
                if existed:
                    setattr(self.actor, attribute, old)
                else:
                    delattr(self.actor, attribute)

    def test_zero_pp_can_use_ordinary_battle_ether_then_later_signature(self):
        """Ultra never grants PP; actual +item restores the independently paid source."""
        self.activate("Lunala", photon_pp=0)
        self.buy("Ether", price=100, quantity=1)
        with patch.object(self.session, "maybe_run_turn"):
            self.record("item", "Ether=3/Photon Geyser")
            self.record("attack", "Growl A1", side=1)
        self.assertEqual(set(self.session.state.declare), {"A1", "B1"}, self.player.messages[-8:])
        self.session.execute_persistent_turn()
        self.assertEqual(ActiveMoveslot.objects.get(pokemon=self.host, slot=1).current_pp, 5)
        self.assertEqual(self.player.trainer.get_item_quantity("Ether"), 0)
        self.attacks(signature=True)
        self.assertEqual(ActiveMoveslot.objects.get(pokemon=self.host, slot=1).current_pp, 4)
        self.assertEqual(self.session.battle.z_used, {"A"})

    def test_sleep_prevention_does_not_pay_photon_or_z_budget(self):
        """A labelled ordinary sleep prerequisite still runs the real prevention pass."""
        self.activate()
        self.actor.status = "slp"
        self.actor.tempvals["sleep_turns"] = 3
        native.core.EVIDENCE.append(
            dict(case=self._testMethodName, fixture="labelled sleep3 after activation")
        )
        self.session._sync_player_pokemon_state(strict=True)
        self.session._persist_turn_state()
        before = ActiveMoveslot.objects.get(pokemon=self.host, slot=1).current_pp
        self.attacks(signature=True)
        self.assertEqual(ActiveMoveslot.objects.get(pokemon=self.host, slot=1).current_pp, before)
        self.assertFalse(self.session.battle.z_used)

    def test_actual_final_ko_commits_and_completed_battle_restores_pair(self):
        """The last real opposing Pokemon may faint without blocking protected sync/end."""
        from pokemon.services.placement import PlacementService

        other = self.players[1]
        for placement in list(
            other.storage.placements.filter(location_type="party").exclude(pokemon=self.foe)
        ):
            PlacementService(other.storage).to_box(placement.pokemon)
        native.core.EVIDENCE.append(
            dict(
                case=self._testMethodName,
                fixture="one ordinary opponent; spare fixture party members boxed before battle",
            )
        )
        self.activate("Lunala")
        if not self.session.battle.battle_over:
            self.attacks(signature=True)
        self.assertTrue(self.session.battle.battle_over)
        before = ActiveMoveslot.objects.get(pokemon=self.host, slot=1).current_pp
        battle = self.session.battle
        self.session.end()
        self.session = None
        self.assertEqual(self.actor.species, "Necrozma-Dawn-Wings")
        self.assertEqual(ActiveMoveslot.objects.get(pokemon=self.host, slot=1).current_pp, before)
        self.assertEqual(battle.ultra_used, {"A"})
        self.separate()

    def test_activation_itself_preserves_live_resources_and_partial_failure_rolls_back(self):
        """Observe actual activation separately from the attack/residual, then inject a fault."""
        from pokemon.battle.ultra_burst import UltraBurst

        self.prepare("Solgaleo")
        self.actor.hp = max(1, self.actor.max_hp - 17)
        self.actor.status = "slp"
        self.actor.tempvals["sleep_turns"] = 3
        self.actor.boosts.update(atk=1, spd=-1)
        self.session._sync_player_pokemon_state(strict=True)
        self.session._persist_turn_state()
        native.core.EVIDENCE.append(
            dict(
                case=self._testMethodName,
                fixture="labelled damage17, sleep3 and earned-stage prerequisites before declaration",
            )
        )

        self.preview()
        self.answer("yes")
        with patch.object(self.session, "execute_persistent_turn"):
            self.attacks()
        before, rng = self.observation(), self.session.battle.rng.getstate()
        with patch.object(
            self.session.battle,
            "start_owned_ability",
            side_effect=RuntimeError("Ultra partial ability fixture"),
        ):
            with self.assertRaisesRegex(RuntimeError, "Ultra partial ability fixture"):
                self.session.execute_persistent_turn()
        self.assertEqual(self.observation(), before)
        self.assertEqual(self.session.battle.rng.getstate(), rng)
        original = UltraBurst.activate
        observations = []

        def observe(battle, participant, actor, request):
            """Run unchanged production activation and compare the surrounding resources."""
            previous = dict(
                hp=actor.hp,
                maximum=actor.max_hp,
                status=actor.status,
                sleep=actor.tempvals["sleep_turns"],
                boosts=deepcopy(actor.boosts),
                pp=[move.pp for move in actor.moves],
                item=actor.item,
            )
            result = original(battle, participant, actor, request)
            self.assertEqual(actor.max_hp - actor.hp, previous["maximum"] - previous["hp"])
            self.assertEqual(
                (
                    actor.status,
                    actor.tempvals["sleep_turns"],
                    actor.boosts,
                    [move.pp for move in actor.moves],
                    actor.item,
                ),
                (
                    previous["status"],
                    previous["sleep"],
                    previous["boosts"],
                    previous["pp"],
                    previous["item"],
                ),
            )
            observations.append(
                dict(
                    before=previous,
                    after=dict(
                        species=str(actor.species),
                        hp=actor.hp,
                        maximum=actor.max_hp,
                        status=actor.status,
                        sleep=actor.tempvals["sleep_turns"],
                        boosts=deepcopy(actor.boosts),
                        pp=[move.pp for move in actor.moves],
                    ),
                )
            )
            return result

        with patch.object(UltraBurst, "activate", side_effect=observe):
            self.session.execute_persistent_turn()
        self.assertEqual(len(observations), 1)
        native.core.EVIDENCE.append(
            dict(
                case=self._testMethodName,
                event="actual-activation-resource-boundary",
                observations=observations,
            )
        )

    def test_earned_ev_progress_survives_ultra_rebuild_end_and_separation(self):
        """Deliver real progression separately; restoration must not freeze old stats."""
        from pokemon.models.stats import add_evs
        from pokemon.services.ownership import fresh_owned

        self.activate("Lunala")
        current = fresh_owned(self.host.pk)
        add_evs(current, {"hp": 8, "special_attack": 8})
        expected = OwnedPokemon.objects.filter(pk=self.host.pk).values_list("evs", flat=True).get()
        native.core.EVIDENCE.append(
            dict(
                case=self._testMethodName,
                fixture="separate ordinary progression-service EV delivery after activation",
                evs=expected,
            )
        )
        self.rebuild()
        self.refresh_actor()
        self.assertEqual(self.actor.species, "Necrozma-Ultra")
        self.session.end()
        self.session = None
        self.separate()
        self.assertEqual(
            OwnedPokemon.objects.filter(pk=self.host.pk).values_list("evs", flat=True).get(),
            expected,
        )


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        native.core.load_runtime()
        from django.apps import apps
        from django.db import connection
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.models.necrozma import NecrozmaCombination, NecrozmaResource
        from pokemon.models.storage import PokemonPlacement
        from pokemon.names import normalize_name
        from pokemon.services.placement_audit import audit_placements_v3

        with connection.schema_editor() as editor:
            importlib.import_module("pokemon.migrations.0041_placement_integrity_triggers").install(
                apps, editor
            )
            importlib.import_module("pokemon.migrations.0058_necrozma_integrity").install(
                apps, editor
            )
        import evennia
        from evennia.commands.command import Command
        from evennia.commands.cmdset import CmdSet

        with patch.object(evennia, "Command", Command), patch.object(evennia, "CmdSet", CmdSet):
            from commands.player import (
                cmd_necrozma,
                cmd_battle_zmove,
                cmd_battle_concede,
                cmd_movesets,
                cmd_learn_evolve,
                cmd_battle_ultra,
            )
        native.core.acquisition.COMMANDS.update(
            {
                "necrozma": (cmd_necrozma, cmd_necrozma.CmdNecrozma),
                "zmove": (cmd_battle_zmove, cmd_battle_zmove.CmdBattleZMove),
                "concede": (cmd_battle_concede, cmd_battle_concede.CmdBattleConcede),
                "movesets": (cmd_movesets, cmd_movesets.CmdMovesets),
                "teach": (cmd_learn_evolve, cmd_learn_evolve.CmdTeachMove),
            }
        )
        for name in (
            "apps",
            "OwnedPokemon",
            "ActiveMoveslot",
            "NecrozmaCombination",
            "NecrozmaResource",
            "PokemonPlacement",
            "audit_placements_v3",
            "normalize_name",
        ):
            setattr(native, name, globals()[name])
            setattr(preparation, name, globals()[name])
        try:
            selected = os.environ.get("PF2_ULTRA_CASES", "").split()
            suite = (
                unittest.TestSuite(UltraBattleCases(name) for name in selected)
                if selected
                else unittest.defaultTestLoader.loadTestsFromTestCase(UltraBattleCases)
            )
            result = unittest.TextTestRunner(verbosity=2).run(suite)
        finally:
            if os.environ.get("PF2_ULTRA_EVIDENCE"):
                Path(os.environ["PF2_ULTRA_EVIDENCE"]).write_text(
                    json.dumps(native.core.EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8"
                )
        raise SystemExit(not result.wasSuccessful())

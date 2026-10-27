"""Ordinary X-item declarations, paid turns and rollback in private PostgreSQL."""

import json
import os
import random
from pathlib import Path
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import battle_item_validation_cases as fixtures

EVIDENCE = []
ITEMS = {
    "X Attack": "attack",
    "X Defense": "defense",
    "X Sp. Atk": "special_attack",
    "X Sp. Def": "special_defense",
    "X Speed": "speed",
    "X Accuracy": "accuracy",
}
CONDITIONS = ("Dire Hit", "Guard Spec.")


class BattleBoosterCases(fixtures.ItemSessionFixture):
    """Exercise real +item, production checkpoints and fresh inventory/ownership."""

    def setUp(self):
        """Expose the real room's SQL Attributes on the captured transport facade."""
        super().setUp()
        self.room.db_attributes = fixtures.ObjectDB.objects.get(pk=self.room.pk).db_attributes

    def actor(self, side=0, index=0):
        """Resolve only the session's current runtime actor after each rebuild."""
        return self.session.battle.participants[side].active[index]

    def record(self, item, *, player=None):
        """Retain independently observed commands and before/after SQL/runtime state."""
        player = player or self.player
        before, start = self.snapshot(), len(player.messages)
        self.command(item, player=player)
        EVIDENCE.append(
            {
                "case": self.id(),
                "command": "+item " + item,
                "before": before,
                "after": self.snapshot(),
                "messages": player.messages[start:],
            }
        )

    def flow(self, item, kind="wild", doubles=False):
        """Every named effect pays once, reconstructs, and never changes owned genetics."""
        self.give(item, 1)
        self.start(kind, doubles)
        before = self.snapshot()
        self.record("A1 " + item + "=1")
        if kind == "pvp":
            if doubles:
                self.command("A2 Splash", "attack")
                self.command("B2 Splash", "attack", self.players[1])
            self.command("B1 Splash", "attack", self.players[1])
        self.assertEqual(
            self.session.battle.turn_count, before["turn"] + 1, self.player.messages[-8:]
        )
        self.assert_effect(item)
        self.assertEqual(self.player.trainer.get_item_quantity(item), 0)
        self.assertEqual(self.snapshot()["owned"], before["owned"])
        for _ in range(2):
            self.rebuild()
            self.assert_effect(item)
            self.assertEqual(self.player.trainer.get_item_quantity(item), 0)
        self.assertFalse(getattr(self.session.battle, "_callback_failures", []))

    def assert_effect(self, item):
        """Inspect reconstructed actual stages or source-bound shared conditions."""
        if item == "Dire Hit":
            state = self.actor().volatiles["focusenergy"]
            self.assertIs(state["source"], self.actor())
            self.assertIs(state["target"], self.actor())
            self.assertEqual(state["sourceEffect"], "item:direhit")
        elif item == "Guard Spec.":
            state = self.actor().side.conditions["mist"]
            self.assertEqual(state["duration"], 4)
            self.assertIs(state["source"], self.actor())
            self.assertEqual(state["sourceEffect"], "item:guardspec")
        else:
            self.assertEqual(self.actor().boosts[ITEMS[item]], 2)

    def test_capped_rejection_leaves_action_stock_and_sibling_free(self):
        """An existing +6 stage is rejected before declaration, preserving a sibling."""
        for item in ITEMS:
            self.give(item, 1)
        self.start("pvp", True)
        self.command("A2 Splash", "attack")
        for item, stat in ITEMS.items():
            self.actor().boosts[stat] = 6
            before = self.snapshot()
            self.record("A1 " + item + "=1")
            self.assertEqual(self.snapshot(), before)
        self.assertIn("A2", self.session.state.declare)

    def test_target_actor_and_selector_refusals_leave_resources_unchanged(self):
        """Only a conscious own active actor can target itself; reserves/moves reject."""
        self.give("X Attack", 1)
        self.start("pvp", True)
        for args in (
            "X Attack",
            "A1 X Attack=2",
            "A1 X Attack=3",
            "A1 X Attack=1/Tackle",
            "B1 X Attack=1",
        ):
            before = self.snapshot()
            self.record(args)
            self.assertEqual(self.snapshot(), before)

    def test_embargo_refuses_but_magic_room_and_heal_block_do_not(self):
        """New bag effects obey selected target policy, independent of held suppression."""
        self.give("X Attack", 1)
        self.start()
        self.actor().volatiles["embargo"] = {"duration": 5}
        before = self.snapshot()
        self.record("X Attack=1")
        self.assertEqual(self.snapshot(), before)
        self.actor().volatiles.pop("embargo")
        self.actor().volatiles["healblock"] = {"duration": 5}
        self.session.battle.field.pseudo_weather["magicroom"] = {"duration": 5}
        self.record("X Attack=1")
        self.assertEqual(self.actor().boosts["attack"], 2)
        self.assertEqual(self.player.trainer.get_item_quantity("X Attack"), 0)

    def test_pending_actor_and_target_survive_rebuild_before_execution(self):
        """Restoring a pending declaration preserves actual slot/controller identity."""
        self.give("X Defense", 1)
        self.start("pvp", True)
        self.command("A1 Splash", "attack")
        self.record("A2 X Defense=2")
        self.rebuild()
        pending = self.session.battle.participants[0].pending_action
        action = next(action for action in pending if action.item)
        self.assertIs(action.pokemon, self.actor(index=1))
        self.assertIs(action.target_pokemon, action.pokemon)
        self.command("B1 Splash", "attack", self.players[1])
        self.command("B2 Splash", "attack", self.players[1])
        self.assertEqual(self.actor(index=1).boosts["defense"], 2)
        self.assertEqual(self.actor().boosts.get("defense", 0), 0)
        self.assertEqual(self.player.trainer.get_item_quantity("X Defense"), 0)

    def pending_turn(self, item="X Attack"):
        """Queue both ordinary sides while withholding automatic execution."""
        self.give(item, 1)
        self.start("pvp")
        self.record(item + "=1")
        with patch.object(self.session, "maybe_run_turn"):
            self.command("B1 Splash", "attack", self.players[1])

    def test_checkpoint_failure_restores_effect_copy_and_retryable_input(self):
        """Fail after real runtime, bag and owned-state writes; retry commits only once."""
        self.pending_turn()
        before = self.snapshot()
        with patch.object(
            self.session,
            "_sync_active_battle_state",
            side_effect=RuntimeError("booster checkpoint fixture"),
        ):
            with self.assertRaisesRegex(RuntimeError, "checkpoint fixture"):
                self.session.execute_persistent_turn()
        after = self.snapshot()
        for key in ("turn", "runtime", "inventory", "owned", "moves", "pending"):
            self.assertEqual(after[key], before[key], key)
        self.session.execute_persistent_turn()
        self.assertEqual(self.actor().boosts["attack"], 2)
        self.assertEqual(self.player.trainer.get_item_quantity("X Attack"), 0)

    def test_partial_debit_failure_rolls_back_complete_turn(self):
        """A failed writer after actual bag SQL cannot leave free stages or a lost copy."""
        from pokemon.models.trainer import Trainer

        self.pending_turn()
        before = self.snapshot()
        original = Trainer.remove_item

        def partial(trainer, *args, **kwargs):
            """Keep the production debit before faulting its return value."""
            original(trainer, *args, **kwargs)
            return False

        with patch.object(Trainer, "remove_item", partial):
            with self.assertRaisesRegex(ValueError, "debit failed"):
                self.session.execute_persistent_turn()
        after = self.snapshot()
        for key in ("turn", "runtime", "inventory", "owned", "moves", "pending"):
            self.assertEqual(after[key], before[key], key)

    def test_queued_redundancy_spends_turn_but_no_copy(self):
        """A legal earlier normal action can make a queued stage increase redundant."""
        from pokemon.utils.boosts import apply_boost

        self.pending_turn()
        original = self.session.battle.execute_actions

        def earlier(actions):
            """Apply an ordinary capped stage event before the already queued bag action."""
            apply_boost(
                self.actor(), {"atk": 6}, source=self.actor(), effect="fixture earlier action"
            )
            return original(actions)

        turn = self.session.battle.turn_count
        with patch.object(self.session.battle, "execute_actions", earlier):
            self.session.execute_persistent_turn()
        self.assertEqual(self.session.battle.turn_count, turn + 1)
        self.assertEqual(self.actor().boosts["attack"], 6)
        self.assertEqual(self.player.trainer.get_item_quantity("X Attack"), 1)

    def test_last_copy_is_reserved_for_only_one_doubles_actor(self):
        """A sibling cannot declare a second useful use against the same last copy."""
        self.give("X Attack", 1)
        self.start("pvp", True)
        self.record("A1 X Attack=1")
        before = self.snapshot()
        self.record("A2 X Attack=2")
        self.assertEqual(self.snapshot(), before)
        self.command("A2 Splash", "attack")
        self.command("B1 Splash", "attack", self.players[1])
        self.command("B2 Splash", "attack", self.players[1])
        self.assertEqual(self.actor().boosts["attack"], 2)
        self.assertEqual(self.actor(index=1).boosts.get("attack", 0), 0)
        self.assertEqual(self.player.trainer.get_item_quantity("X Attack"), 0)

    def test_stale_stock_rejects_the_whole_turn_without_opponent_pp_or_effect(self):
        """A missing queued bag copy is a checkpoint conflict, never a free boost."""
        self.pending_turn()
        self.player.trainer.remove_item("X Attack")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "copy is unavailable"):
            self.session.execute_persistent_turn()
        after = self.snapshot()
        for key in ("turn", "runtime", "inventory", "owned", "moves", "pending"):
            self.assertEqual(after[key], before[key], key)

    def test_stale_owned_actor_rolls_back_without_retargeting(self):
        """Current SQL owner wins over the saved actor's trainer or identity cache."""
        self.pending_turn()
        old_trainer = self.mon.trainer_id
        fixtures.OwnedPokemon.objects.filter(pk=self.mon.pk).update(
            trainer_id=self.players[1].trainer.pk
        )
        before = self.snapshot()
        try:
            with self.assertRaisesRegex(ValueError, "eligible party"):
                self.session.execute_persistent_turn()
            after = self.snapshot()
            for key in ("turn", "runtime", "inventory", "owned", "moves", "pending"):
                self.assertEqual(after[key], before[key], key)
        finally:
            self.state(self.mon, trainer_id=old_trainer)

    def test_stale_checkpoint_refuses_before_any_turn_or_debit(self):
        """A second saved-state writer cannot replay a paid booster turn."""
        self.pending_turn()
        saved = dict(self.session.storage.get("state"))
        changed = dict(saved, mechanic_turn=saved.get("mechanic_turn", 0) + 1)
        self.session.storage.set("state", changed)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "turn changed"):
            self.session.execute_persistent_turn()
        self.assertEqual(self.snapshot(), before)
        self.session.storage.set("state", saved)

    def test_unreviewed_format_rejection_preserves_existing_actions(self):
        """Four-controller or other unreviewed forms never acquire a new bag action."""
        self.give("X Attack", 1)
        self.start("pvp", True)
        self.command("A2 Splash", "attack")
        battle = self.session.battle
        original = list(battle.participants)
        battle.participants = original + original
        try:
            before = self.snapshot()
            self.record("A1 X Attack=1")
            self.assertEqual(self.snapshot(), before)
        finally:
            battle.participants = original

    def race_last_copy(self, item):
        """Separate connections race two actors; the room lock preserves the one winner."""
        from django.db import close_old_connections

        self.give(item, 1)
        self.start("pvp", True)
        barrier = Barrier(2)

        def writer(index):
            """Keep the competing command connection private until its commit."""
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                self.command(f"A{index} {item}={index}")
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(writer, (1, 2)))
        declarations = self.session.state.declare
        self.assertEqual(
            set(declarations) & {"A1", "A2"}, {"A1"} if "A1" in declarations else {"A2"}
        )
        self.assertEqual(len(declarations), 1)
        winner = 0 if "A1" in declarations else 1
        other = 2 if winner == 0 else 1
        self.command(f"A{other} Splash", "attack")
        self.command("B1 Splash", "attack", self.players[1])
        self.command("B2 Splash", "attack", self.players[1])
        self.assertEqual(self.player.trainer.get_item_quantity(item), 0)
        if item in ITEMS:
            self.assertEqual(self.actor(index=winner).boosts[ITEMS[item]], 2)
            self.assertEqual(self.actor(index=1 - winner).boosts.get(ITEMS[item], 0), 0)
        elif item == "Dire Hit":
            self.assertIn("focusenergy", self.actor(index=winner).volatiles)
            self.assertNotIn("focusenergy", self.actor(index=1 - winner).volatiles)
        else:
            self.assertEqual(self.actor().side.conditions["mist"]["duration"], 4)
        EVIDENCE.append(
            {
                "case": self.id(),
                "kind": "separate SQL connection final-copy declarations",
                "item": item,
                "winner": winner + 1,
                "after": self.snapshot(),
            }
        )

    def condition_fault(self, item, fault):
        """Each condition preserves all resources across real write/checkpoint/outer faults."""
        from django.db import transaction
        from pokemon.models.trainer import Trainer

        self.pending_turn(item)
        before, offset = self.snapshot(), len(self.player.messages)
        if fault == "checkpoint":
            manager = patch.object(
                self.session,
                "_sync_active_battle_state",
                side_effect=RuntimeError("condition checkpoint fixture"),
            )
            with manager, self.assertRaisesRegex(RuntimeError, "checkpoint fixture"):
                self.session.execute_persistent_turn()
        elif fault == "debit":
            original = Trainer.remove_item

            def debit(trainer, *args, **kwargs):
                """Fault only after actual bag SQL."""
                original(trainer, *args, **kwargs)
                return False

            with (
                patch.object(Trainer, "remove_item", debit),
                self.assertRaisesRegex(ValueError, "debit failed"),
            ):
                self.session.execute_persistent_turn()
        else:
            with transaction.atomic(), self.assertRaisesRegex(ValueError, "containing transaction"):
                self.session.execute_persistent_turn()
        after = self.snapshot()
        for key in ("turn", "runtime", "inventory", "owned", "moves", "pending"):
            self.assertEqual(after[key], before[key], key)
        self.assertEqual(self.player.messages[offset:], [])
        self.session.execute_persistent_turn()
        self.assert_effect(item)
        self.assertEqual(self.player.trainer.get_item_quantity(item), 0)

    def repeated_condition(self, item):
        """An active Focus Energy/Mist copy rejects before declaration without refreshing."""
        self.give(item, 2)
        self.start()
        self.record(item + "=1")
        before = self.snapshot()
        self.record(item + "=1")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.player.trainer.get_item_quantity(item), 1)

    def test_mist_player_flow_blocks_opposing_growl_through_expiry(self):
        """Actual +item/+attack turns count activation, restore and later normal expiry."""
        from pokemon.services.move_management import initialize_generated_moveset

        initialize_generated_moveset(self.owned[1][0], active_move_names=["Growl", "Splash"])
        self.give("Guard Spec.", 1)
        self.start("pvp")
        self.record("Guard Spec.=1")
        self.command("B1 Growl", "attack", self.players[1])
        self.assertEqual(self.actor().boosts.get("attack", 0), 0)
        for duration in (3, 2, 1, 0):
            self.rebuild()
            self.command("A1 Splash", "attack")
            self.command("B1 Growl", "attack", self.players[1])
            self.assertEqual(self.actor().boosts.get("attack", 0), 0)
            if duration:
                self.assertEqual(self.actor().side.conditions["mist"]["duration"], duration)
            else:
                self.assertNotIn("mist", self.actor().side.conditions)
        self.command("A1 Splash", "attack")
        self.command("B1 Growl", "attack", self.players[1])
        self.assertEqual(self.actor().boosts["attack"], -1)

    def test_paid_stages_and_focus_clear_on_ordinary_end(self):
        """Battle cleanup cannot leak temporary stages or crit state to a later session."""
        for item in ("X Attack", "Dire Hit", "Guard Spec."):
            self.give(item, 1)
        self.start()
        for item in ("X Attack", "Dire Hit", "Guard Spec."):
            self.record(item + "=1")
        holder = self.actor()
        self.session.end()
        self.assertFalse(holder.boosts)
        self.assertNotIn("focusenergy", holder.volatiles)
        self.assertNotIn("mist", holder.side.conditions)

    def ability_flow(self, species, ability, amount, uses):
        """A genuinely native ability modifies paid X outcomes through the normal event path."""
        from pokemon.services.placement import PlacementService

        PlacementService(self.player.storage).to_box(self.mon)
        self.mon = fixtures.create_owned_pokemon(
            species,
            self.player.trainer,
            20,
            nature="Hardy",
            ability=ability,
            ivs=[0] * 6,
            evs=[0] * 6,
            active_move_names=["Tackle" if species == "Bidoof" else "Withdraw"],
        )
        PlacementService(self.player.storage).to_party(self.mon, slot=1)
        self.owned[0][0] = self.mon
        self.give("X Attack", uses + 1)
        self.start()
        before = self.snapshot()["owned"]
        self.record("X Attack=1")
        self.assertEqual(self.actor().boosts["attack"], amount)
        self.rebuild()
        for _ in range(uses - 1):
            self.record("X Attack=1")
        self.assertEqual(self.actor().boosts["attack"], 6 if amount > 0 else -6)
        capped = self.snapshot()
        self.record("X Attack=1")
        self.assertEqual(self.snapshot(), capped)
        self.assertEqual(self.player.trainer.get_item_quantity("X Attack"), 1)
        self.assertEqual(self.snapshot()["owned"], before)

    def test_native_simple_changes_paid_x_item_and_caps_usefully(self):
        """Native Bidoof's Simple gives +4 then a useful partial +2 without wasting a capped copy."""
        self.ability_flow("Bidoof", "Simple", 4, 2)

    def test_native_contrary_reverses_paid_x_item_and_preserves_negative_cap(self):
        """Native Shuckle's Contrary lowers Attack to -6 and then refuses a fourth copy."""
        self.ability_flow("Shuckle", "Contrary", -2, 3)

    def test_dire_hit_rebuilt_player_attack_produces_a_real_critical(self):
        """A paid restored Focus Energy reaches a later ordinary Tackle damage calculation."""
        from pokemon.battle import damage

        self.give("Dire Hit", 1)
        self.start()
        self.record("Dire Hit=1")
        self.rebuild()
        observed = []
        original = damage.damage_calc

        def observe(*args, **kwargs):
            """Capture the real result without changing damage, crits or prevention."""
            result = original(*args, **kwargs)
            if args[0] is self.actor():
                observed.append(result.debug)
            return result

        class CriticalRoll(random.Random):
            """Choose a legal half-probability critical boundary, not a forced-critical move."""

            def random(self):
                return 0.25

        self.session.battle.rng = CriticalRoll(21)
        with patch.object(damage, "damage_calc", observe):
            self.command("A1 Tackle", "attack")
        self.assertTrue(observed)
        self.assertEqual(observed[0]["critical"], [True])
        self.assertGreater(sum(observed[0]["damage"]), 0)
        self.assertEqual(self.player.trainer.get_item_quantity("Dire Hit"), 0)
        EVIDENCE.append(
            {
                "case": self.id(),
                "kind": "paid rebuilt ordinary Tackle critical",
                "actual_damage": observed,
            }
        )


def add_flow(item, kind, doubles=False):
    """Count each named item/format independently through the real command path."""

    def test(self):
        """Execute this exact named bag item, then reconstruct its completed checkpoint."""
        self.flow(item, kind, doubles)

    setattr(
        BattleBoosterCases,
        "test_"
        + item.replace(" ", "").replace(".", "")
        + "_"
        + kind
        + ("_double" if doubles else ""),
        test,
    )


for item in [*ITEMS, *CONDITIONS]:
    for kind in ("wild", "trainer", "pvp"):
        add_flow(item, kind)
    add_flow(item, "pvp", True)

    def race_case(self, selected=item):
        """Race two real SQL connections for the same final bag copy."""
        self.race_last_copy(selected)

    setattr(BattleBoosterCases, "test_race_" + item.replace(" ", "").replace(".", ""), race_case)

for item in CONDITIONS:

    def repeat_case(self, selected=item):
        """An already active shared condition has no action or debit cost."""
        self.repeated_condition(selected)

    setattr(
        BattleBoosterCases, "test_repeat_" + item.replace(" ", "").replace(".", ""), repeat_case
    )
    for fault in ("debit", "checkpoint", "outer"):

        def fault_case(self, selected=item, failure=fault):
            """The named condition survives this actual persistent boundary failure."""
            self.condition_fault(selected, failure)

        setattr(
            BattleBoosterCases,
            "test_" + fault + "_" + item.replace(" ", "").replace(".", ""),
            fault_case,
        )


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        fixtures.load_runtime()
        try:
            result = unittest.TextTestRunner(verbosity=2).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(BattleBoosterCases)
            )
        finally:
            if os.environ.get("PF2_BOOSTER_EVIDENCE"):
                Path(os.environ["PF2_BOOSTER_EVIDENCE"]).write_text(
                    json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8"
                )
        raise SystemExit(not result.wasSuccessful())

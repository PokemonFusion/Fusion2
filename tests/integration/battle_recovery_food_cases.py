"""Exercise #773's named manual bag recovery through production +item turns.

Requires an explicit disposable PostgreSQL endpoint. Setup creates tagged SQL
fixtures, while player input uses production parsing, choices, queue, complete
turns and checkpoint rebuilds. No live login, game database or service changes.
"""

import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import battle_item_validation_cases as fixtures
from isolated_postgres import IsolatedPostgres

EVIDENCE = []
HP_ITEMS = {
    "Fresh Water": 30, "Soda Pop": 50, "Lemonade": 70, "Moomoo Milk": 100,
    "Sweet Heart": 20, "Oran Berry": 10, "Sitrus Berry": "quarter",
    "Berry Juice": 20, "Berry": 10, "Gold Berry": 30,
}
STATUS_ITEMS = {
    "Lava Cookie": "slp", "Old Gateau": "psn", "Casteliacone": "tox",
    "Lumiose Galette": "brn", "Shalour Sable": "frz", "Big Malasada": "par",
    "Pewter Crunchies": "slp", "Cheri Berry": "par", "Chesto Berry": "slp",
    "Pecha Berry": "tox", "Rawst Berry": "brn", "Aspear Berry": "frz",
    "Lum Berry": "psn", "Burnt Berry": "frz", "Ice Berry": "brn",
    "Mint Berry": "slp", "Miracle Berry": "tox", "PRZ Cure Berry": "par",
    "PSN Cure Berry": "psn",
}
PP_ITEMS = {"Leppa Berry": 10, "Mystery Berry": 5}


class BattleRecoveryFoodCases(fixtures.ItemSessionFixture):
    """Verify every enabled name and bounded targeting/atomicity regressions."""

    fixture_level = 100

    def row(self, mon=None):
        """Read fresh SQL fields independently of Evennia's identity cache."""
        return fixtures.OwnedPokemon.objects.filter(pk=(mon or self.mon).pk).values().get()

    def pp(self, mon=None):
        """Read all active move slots in canonical order."""
        return list(fixtures.ActiveMoveslot.objects.filter(pokemon=mon or self.mon)
                    .order_by("slot").values_list("current_pp", flat=True))

    def proof_state(self):
        """Retain reviewable effects, bags, actors and checkpoint identities."""
        snapshot = self.snapshot()
        return {key: snapshot[key] for key in (
            "turn", "inventory", "inventory_cache", "moves", "placements", "pending",
            "controls", "runtime", "persisted_state", "owned")}

    def recorded(self, args, *, label="player-use", player=None):
        """Record exact normal command input, output and independent state."""
        player = player or self.player
        before, offset = self.proof_state(), len(player.messages)
        self.command(args, player=player)
        EVIDENCE.append({"label": label, "command": "+item " + args,
                         "before": before, "after": self.proof_state(),
                         "messages": player.messages[offset:]})

    def persisted(self, item, mon=None):
        """Rebuild a completed checkpoint twice; never replay a paid item."""
        mon = mon or self.mon
        expected, pp, quantity = self.row(mon), self.pp(mon), self.player.trainer.get_item_quantity(item)
        for _ in range(2):
            self.rebuild()
            self.assertEqual(self.row(mon), expected)
            self.assertEqual(self.pp(mon), pp)
            self.assertEqual(self.player.trainer.get_item_quantity(item), quantity)
            runtime = next(p for p in self.session.battle.participants[0].pokemons
                           if p.model_id == "owned:" + str(mon.pk))
            self.assertEqual(runtime.hp, expected["current_hp"])
            self.assertEqual(runtime.status or "", expected["status"])
            self.assertEqual([m.pp for m in runtime.moves], pp)

    def check_item(self, item):
        """Each of the 32 names uses its real action, debit, effect and reload."""
        mon = self.owned[0][2] if item in PP_ITEMS or item == "Max Honey" else self.mon
        target = "3" if mon is not self.mon else "1"
        status = STATUS_ITEMS.get(item, "")
        self.state(mon, current_hp=0 if item == "Max Honey" else 1,
                   status=status, sleep_turns=2 if status == "slp" else None, friendship=137)
        if item in PP_ITEMS:
            fixtures.ActiveMoveslot.objects.filter(pokemon=mon, slot__in=[2, 3]).update(current_pp=0)
        self.give(item)
        self.start()
        before = self.row(mon)
        self.recorded(item + "=" + target + ("/Water Gun" if item in PP_ITEMS else ""))
        after = self.row(mon)
        self.assertEqual(self.session.battle.turn_count, 2)
        self.assertEqual(self.player.trainer.get_item_quantity(item), 1)
        self.assertEqual(after["friendship"], 137)
        if item in HP_ITEMS:
            amount = fixtures.get_max_hp(mon) // 4 if HP_ITEMS[item] == "quarter" else HP_ITEMS[item]
            self.assertEqual(after["current_hp"], min(fixtures.get_max_hp(mon), 1 + amount))
        elif item in STATUS_ITEMS:
            self.assertEqual((after["status"], after["sleep_turns"]), ("", None))
            self.assertEqual(after["current_hp"], 1)
        elif item in PP_ITEMS:
            self.assertEqual(self.pp(mon), [40, 0, PP_ITEMS[item]])
        else:
            self.assertEqual(after["current_hp"], fixtures.get_max_hp(mon))
        for field in ("held_item", "evs", "ivs", "flags", "level", "total_exp", "ability"):
            self.assertEqual(after[field], before[field], field)
        self.persisted(item, mon)

    def test_allowlist_is_exactly_the_reviewed_32_existing_items(self):
        """Future field additions cannot silently expand manual battle support."""
        from pokemon.services.battle_items import BattleMedicineUse
        from pokemon.names import normalize_name

        enabled = (set(BattleMedicineUse.healing) | set(BattleMedicineUse.fractions)
                   | set(BattleMedicineUse.statuses) | set(BattleMedicineUse.revivals)
                   | set(BattleMedicineUse.pp_items)) - BattleMedicineUse.standard_items
        expected = {normalize_name(name) for name in [*HP_ITEMS, *STATUS_ITEMS, *PP_ITEMS, "Max Honey"]}
        self.assertEqual(len(expected), 32)
        self.assertEqual(enabled, expected)

    def test_unsupported_berries_and_field_items_never_reserve_an_action(self):
        """No broad berry/food fallback crosses the reviewed eligibility boundary."""
        items = ("Figy Berry", "Wiki Berry", "Mago Berry", "Aguav Berry", "Iapapa Berry",
                 "Pomeg Berry", "Kelpsy Berry", "Qualot Berry", "Hondew Berry", "Grepa Berry",
                 "Tamato Berry", "Sacred Ash", "Persim Berry", "Bitter Berry", "Razz Berry",
                 "Lansat Berry", "PP Up", "Rare Candy", "Leftovers", "Rage Candy Bar", "Hopo Berry")
        for item in items:
            self.give(item)
        self.start()
        before = self.snapshot()
        for item in items:
            self.recorded(item + "=1", label="unsupported-no-action")
            self.assertEqual(self.snapshot(), before)

    def test_missing_stock_and_foreign_or_unresolved_targets_do_not_queue(self):
        """Owned target resolution never substitutes an opponent or boxed member."""
        self.give("Fresh Water")
        self.start()
        before = self.snapshot()
        for args in ("Oran Berry", "Fresh Water=6", "Fresh Water=B1",
                     "Fresh Water=" + str(self.owned[1][0].pk), "B1 Fresh Water=1"):
            self.recorded(args, label="missing-stock-or-wrong-target")
            self.assertEqual(self.snapshot(), before)

    def test_queued_pp_keeps_reserve_move_and_actor_through_rebuild(self):
        """A waiting PvP declaration restores only its selected reserve move."""
        reserve = self.owned[0][2]
        fixtures.ActiveMoveslot.objects.filter(pokemon=reserve).update(current_pp=0)
        self.give("Mystery Berry")
        self.start("pvp")
        self.recorded("A1 Mystery Berry=3/3", label="queued-reserve-pp")
        self.rebuild()
        action = self.session.battle.participants[0].pending_action
        self.assertEqual((action.item_move, action.target_pokemon.model_id), ("3", "owned:" + str(reserve.pk)))
        self.command("B1 Splash", "attack", self.players[1])
        self.assertEqual(self.pp(reserve), [0, 0, 5])
        self.assertEqual(self.player.trainer.get_item_quantity("Mystery Berry"), 1)
        self.persisted("Mystery Berry", reserve)

    def test_selected_pp_caps_at_boosted_capacity_and_never_uses_another_move(self):
        """Full/invalid selected slots spend the action, never a fallback debit."""
        reserve = self.owned[0][2]
        move = fixtures.ActiveMoveslot.objects.get(pokemon=reserve, slot=3).move
        fixtures.MovePPBoost.objects.create(pokemon=reserve, move=move, bonus_pp=15)
        fixtures.ActiveMoveslot.objects.filter(pokemon=reserve, slot=2).update(current_pp=0)
        fixtures.ActiveMoveslot.objects.filter(pokemon=reserve, slot=3).update(current_pp=37)
        self.give("Leppa Berry", 3)
        self.start()
        self.recorded("Leppa Berry=3/Water Gun")
        self.assertEqual(self.pp(reserve), [40, 0, 40])
        for selector in ("Water Gun", "99", "Missing Move"):
            self.recorded("Leppa Berry=3/" + selector, label="pp-no-effect")
            self.assertEqual(self.pp(reserve), [40, 0, 40])
            self.assertEqual(self.player.trainer.get_item_quantity("Leppa Berry"), 2)
        self.recorded("Leppa Berry=3", label="pp-first-depleted-default")
        self.assertEqual(self.pp(reserve), [40, 10, 40])
        self.assertEqual(self.player.trainer.get_item_quantity("Leppa Berry"), 1)

    def test_no_effect_policy_for_hp_status_revival_and_fainted_pp(self):
        """Supported no-effect commands cost a turn while preserving inventory."""
        reserve = self.owned[0][2]
        self.state(reserve, current_hp=0)
        for item in ("Fresh Water", "Oran Berry", "Pecha Berry", "Max Honey", "Mystery Berry"):
            self.give(item)
        self.start()
        for args in ("Fresh Water=1", "Oran Berry=3", "Pecha Berry=1", "Max Honey=1", "Mystery Berry=3/3"):
            before = self.snapshot()
            self.recorded(args, label="supported-no-effect")
            after = self.snapshot()
            self.assertEqual(after["turn"], before["turn"] + 1)
            for field in ("owned", "inventory", "placements", "moves"):
                self.assertEqual(after[field], before[field], field)

    def test_doubles_each_controller_owns_actor_target_and_bag(self):
        """Both sides' paired actions keep independent bag/held state after reload."""
        for roster in self.owned:
            for mon in roster[:2]:
                self.state(mon, current_hp=1)
        self.give("Fresh Water")
        self.give("Gold Berry")
        self.give("Berry Juice", player=self.players[1])
        self.give("Sweet Heart", player=self.players[1])
        self.start("pvp", doubles=True)
        self.recorded("A1 Fresh Water=2")
        self.recorded("A2 Gold Berry=1")
        self.rebuild()
        self.recorded("B1 Berry Juice=2", player=self.players[1])
        self.recorded("B2 Sweet Heart=1", player=self.players[1])
        self.assertEqual(self.session.battle.turn_count, 2)
        self.assertEqual([self.row(mon)["current_hp"] for mon in self.owned[0][:2]], [31, 31])
        self.assertEqual([self.row(mon)["current_hp"] for mon in self.owned[1][:2]], [21, 21])
        for item, player in (("Fresh Water", self.player), ("Gold Berry", self.player),
                             ("Berry Juice", self.players[1]), ("Sweet Heart", self.players[1])):
            self.assertEqual(player.trainer.get_item_quantity(item), 1)

    def test_stale_egg_target_is_rechecked_at_execution(self):
        """A target that becomes ineligible while waiting is never fed or debited."""
        self.stale_target("egg")

    def test_stale_owner_is_rechecked_despite_cached_model(self):
        """A queued old owner cannot feed a target after its authoritative transfer."""
        self.stale_target("owner")

    def test_stale_fusion_placement_is_rechecked_despite_cached_placement(self):
        """An inactive Fusion reservation cannot inherit its former party eligibility."""
        self.stale_target("placement")

    def stale_target(self, changed):
        """Inject a stale SQL precondition without refreshing identity-map objects."""
        reserve = self.owned[0][2]
        self.state(reserve, current_hp=1)
        self.give("Fresh Water")
        self.start("pvp")
        self.recorded("A1 Fresh Water=3", label="before-stale-target")
        # Deliberately retain the pre-queue identity-map instance: eligibility
        # must come from the locked SQL row rather than that cached object.
        if changed == "egg":
            fixtures.OwnedPokemon.objects.filter(pk=reserve.pk).update(is_egg=True)
        elif changed == "owner":
            fixtures.OwnedPokemon.objects.filter(pk=reserve.pk).update(trainer=self.players[1].trainer)
        else:
            placement = fixtures.PokemonPlacement.objects.get(pokemon=reserve)
            fixtures.PokemonPlacement.objects.filter(pk=placement.pk).update(location_type="fusion", slot=None)
        self.command("B1 Splash", "attack", self.players[1])
        self.assertEqual(self.row(reserve)["current_hp"], 1)
        self.assertEqual(self.player.trainer.get_item_quantity("Fresh Water"), 2)

    def test_bag_berries_ignore_eating_modifiers_and_preserve_held_copies(self):
        """Native Ripen/Cheek Pouch and opposing Unnerve do not affect bag medicine."""
        self.state(self.mon, species="Applin", ability="Ripen", held_item="Oran Berry")
        ally = self.owned[0][1]
        self.state(ally, species="Dedenne", ability="Cheek Pouch", held_item="Oran Berry")
        self.state(self.owned[1][0], species="Corviknight", ability="Unnerve")
        starts = []
        for mon in (self.mon, ally):
            fresh = fixtures.OwnedPokemon.objects.get(pk=mon.pk)
            hp = fixtures.get_max_hp(fresh) * 3 // 4
            self.state(mon, current_hp=hp)
            starts.append(hp)
        self.give("Oran Berry", 3)
        self.start("pvp")
        foe = self.session.battle.participants[1].active[0]
        self.assertEqual(getattr(foe.ability, "name", foe.ability), "Unnerve")
        for index, mon in enumerate((self.mon, ally), 1):
            self.recorded("A1 Oran Berry=" + str(index), label="bag-versus-held-and-ability")
            self.command("B1 Splash", "attack", self.players[1])
            self.assertEqual(self.row(mon)["current_hp"], starts[index - 1] + 10)
            self.assertEqual(self.row(mon)["held_item"], "Oran Berry")
        self.assertEqual(self.player.trainer.get_item_quantity("Oran Berry"), 1)
        self.persisted("Oran Berry")

    def test_automatic_held_berry_still_activates_separately_from_bag_food(self):
        """A normal residual held activation has its own item source and effect."""
        self.state(held_item="Oran Berry")
        self.give("Fresh Water")
        self.give("Oran Berry", 3)
        self.start()
        # Controlled damage precondition, separate from ordinary player input.
        self.session.battle.participants[0].active[0].hp = 1
        self.state(current_hp=1)
        self.recorded("Fresh Water=1", label="bag-food-and-automatic-held-berry")
        self.assertEqual(self.row()["current_hp"], 41)
        self.assertEqual(self.row()["held_item"], "")
        self.assertEqual(self.player.trainer.get_item_quantity("Fresh Water"), 1)
        self.assertEqual(self.player.trainer.get_item_quantity("Oran Berry"), 3)
        self.persisted("Fresh Water")

    def test_effect_save_failure_after_write_restores_sql_bag_and_runtime(self):
        """An item save that fails after writing cannot leak its effect or debit."""
        self.state(current_hp=1)
        self.give("Fresh Water")
        self.start()
        original = fixtures.OwnedPokemon.save
        faulted = False

        def save_then_fail(mon, *args, **kwargs):
            """Fail exactly the medicine save, allowing normal checkpoint cleanup."""
            nonlocal faulted
            original(mon, *args, **kwargs)
            if mon.pk == self.mon.pk and "friendship" in kwargs.get("update_fields", ()) and not faulted:
                faulted = True
                raise RuntimeError("#773 medicine save fixture")

        with patch.object(fixtures.OwnedPokemon, "save", save_then_fail):
            self.recorded("Fresh Water=1", label="post-effect-write-failure")
        self.assertTrue(faulted)
        self.assertEqual(self.row()["current_hp"], 1)
        self.assertEqual(self.player.trainer.get_item_quantity("Fresh Water"), 2)
        self.persisted("Fresh Water")

    def test_partial_false_inventory_debit_rolls_back_hp_and_pp(self):
        """A broken inventory writer returning false cannot keep its SQL debit."""
        from pokemon.models.trainer import Trainer

        self.state(current_hp=1)
        fixtures.ActiveMoveslot.objects.filter(pokemon=self.mon, slot=3).update(current_pp=0)
        for item in ("Fresh Water", "Mystery Berry"):
            self.give(item)
        self.start()
        original = Trainer.remove_item

        def debit_then_false(trainer, *args, **kwargs):
            """Inject failure after the production inventory write."""
            original(trainer, *args, **kwargs)
            return False

        for args in ("Fresh Water=1", "Mystery Berry=1/3"):
            before = self.snapshot()
            with patch.object(Trainer, "remove_item", debit_then_false):
                self.recorded(args, label="partial-debit-false")
            for field in ("inventory", "owned", "moves"):
                self.assertEqual(self.snapshot()[field], before[field], field)

    def test_checkpoint_failure_restores_bag_runtime_and_retryable_input(self):
        """A failure after medicine execution rolls the entire turn back once."""
        self.checkpoint_failure("Fresh Water", "A1 Fresh Water=1")

    def test_pp_checkpoint_failure_restores_slots_snapshot_and_retryable_input(self):
        """Selected-move PP changes also roll back with the complete turn."""
        self.checkpoint_failure("Mystery Berry", "A1 Mystery Berry=1/3")

    def checkpoint_failure(self, item, args):
        """Fault the real persistent boundary after SQL/runtime medicine effects."""
        self.state(current_hp=1)
        fixtures.ActiveMoveslot.objects.filter(pokemon=self.mon, slot=3).update(current_pp=0)
        self.give(item)
        self.start("pvp")
        self.recorded(args, label="before-checkpoint-failure")
        # Queue the opponent without starting the turn, then fault the real
        # persistent boundary after medicine has changed SQL/runtime state.
        with patch.object(self.session, "maybe_run_turn"):
            self.command("B1 Splash", "attack", self.players[1])
        before = self.snapshot()
        with patch.object(self.session, "_sync_active_battle_state", side_effect=RuntimeError("#773 checkpoint fixture")):
            with self.assertRaisesRegex(RuntimeError, "checkpoint fixture"):
                self.session.execute_persistent_turn()
        after = self.snapshot()
        for field in ("turn", "runtime", "inventory", "owned", "moves", "pending"):
            self.assertEqual(after[field], before[field], field)
        self.session.execute_persistent_turn()
        self.assertEqual(self.row()["current_hp"], 31 if item == "Fresh Water" else 1)
        self.assertEqual(self.pp()[2], 5 if item == "Mystery Berry" else 0)
        self.assertEqual(self.player.trainer.get_item_quantity(item), 1)
        self.persisted(item)


def item_case(item):
    """Expose individual test results for every reviewed item, not one loop pass."""
    def test(self):
        self.check_item(item)
    test.__doc__ = "+item " + item + ": exact effect, one debit, two checkpoint rebuilds."
    return test


for _name in [*HP_ITEMS, *STATUS_ITEMS, *PP_ITEMS, "Max Honey"]:
    setattr(BattleRecoveryFoodCases, "test_player_" + _name.lower().replace(" ", "_"), item_case(_name))


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        fixtures.load_runtime()
        result = unittest.TextTestRunner(verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(BattleRecoveryFoodCases))
        if os.environ.get("PF2_BATTLE_RECOVERY_EVIDENCE"):
            Path(os.environ["PF2_BATTLE_RECOVERY_EVIDENCE"]).write_text(
                json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())

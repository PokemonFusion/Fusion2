"""Prove ordinary Hyper Training commands with real disposable PostgreSQL rows."""

import json
import os
import re
import sys
from pathlib import Path
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
from ui_cases import PlayerView

EVIDENCE = []


class HyperPlayer(PlayerView):
    """Adapt only session transport; use production player identity/storage."""

    def get_pokemon_by_id(self, identifier):
        """Expose the normal owned-ID lookup."""
        return User.get_pokemon_by_id(self, identifier)

    def get_active_pokemon_by_slot(self, slot):
        """Retain canonical party slots and gaps."""
        return User.get_active_pokemon_by_slot(self, slot)

    def get_active_party(self):
        """Use the canonical player's ordinary party view."""
        return User.get_active_party(self)

    def get_box(self, index):
        """Use the ordinary storage destination."""
        return User.get_box(self, index)

    def _pokemon_is_in_party(self, pokemon):
        """Use production deposit eligibility."""
        return User._pokemon_is_in_party(self, pokemon)

    def deposit_pokemon(self, identifier, index=1):
        """Exercise the shipped deposit transition."""
        return User.deposit_pokemon(self, identifier, index)

    def execute_cmd(self, text, **kwargs):
        """Capture the menu's exit look command at the session boundary."""
        self.messages.append("Menu exit: " + text)


class HyperTrainingCases(unittest.TestCase):
    """Check both Bottle Cap field routes, canonical targets, persistence and atomic use."""

    def setUp(self):
        """Create a tagged ordinary owner with a genuinely gapped party."""
        self.character = ObjectDB.objects.create(db_key="hyper-training-770-" + uuid4().hex, db_typeclass_path="pokemon.user.User")
        self.trainer, _ = Trainer.objects.get_or_create(user=self.character, defaults={"trainer_number": Trainer.objects.count() + 1})
        self.storage, _ = UserStorage.objects.get_or_create(user=self.character)
        StorageBox.objects.create(storage=self.storage, name="Hyper Training Box")
        self.player = HyperPlayer(self.character, self.trainer, self.storage)
        self.player.pk = self.character.pk
        self.mon = self.create_mon()
        self.mon.activemoveslot_set.filter(slot=2).update(slot=4)

    def tearDown(self):
        """Release any real menu on this disposable transport."""
        menu = self.player.ndb._evmenu
        if menu:
            menu.close_menu()

    def create_mon(self, slot=3, species="Eevee", level=50):
        """Use production creation and placement, not invented HP/EXP."""
        pokemon = create_owned_pokemon(species, self.trainer, level, nature="Hardy",
                                       ivs=[0] * 6, evs=[0] * 6, active_move_names=["Tackle", "Water Gun"])
        PlacementService(self.storage).to_party(pokemon, slot=slot)
        return pokemon

    def command(self, args, kind="use", player=None):
        """Run the real parser/command; do not substitute an item effect."""
        player = player or self.player
        command = COMMANDS[kind]()
        command.caller, command.args, command.cmdstring = player, args, "+" + kind
        command.parse()
        module = sys.modules[command.__module__]
        if hasattr(module, "get_system"):
            with patch.object(module, "get_system", return_value=SimpleNamespace(battle_manager=None)):
                command.func()
        else:
            command.func()
        return player.messages[-1] if player.messages else ""

    def state(self, pokemon=None, **fields):
        """Set explicit fixture state while leaving stale model caches intact."""
        OwnedPokemon.objects.filter(pk=(pokemon or self.mon).pk).update(**fields)

    def reload(self):
        """Resolve current shared state after a detached progression save."""
        self.mon = OwnedPokemon.objects.get(pk=self.mon.pk)
        FieldMedicineUse._refresh(self.mon, self.snapshot()["pokemon"])
        return self.mon

    def snapshot(self, pokemon=None):
        """Read persisted Pokemon, placement, bag, boost and move rows."""
        identifier = (pokemon or self.mon).pk
        return {
            "pokemon": OwnedPokemon.objects.filter(pk=identifier).values().first(),
            "placement": list(PokemonPlacement.objects.filter(pokemon_id=identifier).values()),
            "inventory_cache": dict(self.character.db.inventory or {}),
            "inventory": list(self.trainer.list_inventory().values("item_name", "quantity")),
            "learned": list(PokemonLearnedMove.objects.filter(pokemon_id=identifier).order_by("move_id").values()),
            "active": list(ActiveMoveslot.objects.filter(pokemon_id=identifier).order_by("slot").values()),
            "boosts": list(MovePPBoost.objects.filter(pokemon_id=identifier).order_by("move_id").values()),
            "sets": list(MovesetSlot.objects.filter(moveset__pokemon_id=identifier).order_by("pk").values()),
        }

    def give(self, item, amount=1):
        """Fixture setup grants bag stock separately from ordinary acceptance."""
        self.trainer.add_item(item, amount)

    def record(self, label, args, pokemon=None):
        """Retain ordinary input/output and independent SQL before/after proof."""
        before, start = self.snapshot(pokemon), len(self.player.messages)
        self.command(args)
        EVIDENCE.append({"label": label, "command": "+use " + args, "before": before,
                         "after": self.snapshot(pokemon), "messages": self.player.messages[start:]})

    def prepare(self, *, ivs=None, flags=None, hp=None):
        """Set genetic values and unrelated state separately from player commands."""
        self.state(ivs=list(ivs if ivs is not None else [0, 1, 2, 3, 4, 5]),
                   flags=list(flags if flags is not None else ["ordinary-hyper-fixture"]),
                   current_hp=1, status="psn", friendship=203, held_item="Leftovers")
        FieldMedicineUse._refresh(self.mon, self.snapshot()["pokemon"])
        self.state(current_hp=max(1, get_max_hp(self.mon) - 17) if hp is None else hp)

    def expected_stats(self, trained, pokemon=None):
        """Calculate expected stats with independent explicit effective IV input."""
        row = self.snapshot(pokemon)["pokemon"]
        ivs = row["ivs"].copy()
        for stat in trained:
            ivs[STATS.index(stat)] = 31
        return get_stats(SimpleNamespace(species=row["species"], level=row["level"],
                                        ivs=ivs, evs=row["evs"], nature=row["nature"]))

    def assert_training(self, before, trained, item, quantity=0):
        """Only legal overlay flags and the required HP delta may change."""
        after = self.snapshot()
        expected_flags = before["pokemon"]["flags"] + ["hypertrained:" + stat for stat in trained]
        self.assertEqual(after["pokemon"]["flags"], expected_flags)
        for key, value in before["pokemon"].items():
            if key not in {"flags", "current_hp"}:
                self.assertEqual(after["pokemon"][key], value, key)
        for key in ("placement", "active", "learned", "sets", "boosts"):
            self.assertEqual(after[key], before[key], key)
        expected = self.expected_stats(HyperTraining.trained(self.mon))
        self.assertEqual(get_stats(self.mon), expected)
        self.assertEqual(self.trainer.get_item_quantity(item), quantity)

    def flow(self, stat=None):
        """Discover, train, display and independently reload either cap route."""
        from django.db import connections
        from utils.pokemon_utils import build_battle_pokemon_from_model

        item = "Bottle Cap" if stat else "Gold Bottle Cap"
        trained = [stat] if stat else list(STATS)
        self.prepare()
        self.give(item)
        self.assertIn("level 50+", self.command(item, "itemdex"))
        self.assertIn(item, self.command("", "inventory"))
        self.assertIn(str(self.mon.pk), self.command("3", "party"))
        before = self.snapshot()
        old_max = get_max_hp(self.mon)
        args = item + "=3" + ("/" + LABELS[STATS.index(stat)] if stat else "")
        self.record("ordinary-hyper-training", args)
        self.assertIn("genetic IVs are unchanged", self.player.messages[-1])
        self.assert_training(before, trained, item)
        expected = self.expected_stats(trained)
        self.assertEqual(self.snapshot()["pokemon"]["current_hp"], before["pokemon"]["current_hp"] + expected["hp"] - old_max)
        details = self.command("3", "party")
        self.assertIn("Effective IV", re.sub(r"\x1b\[[0-9;]*m", "", details))
        self.assertIn("Hyper Trained", details)
        self.assertIn("IV row remains genetic", details)
        connections.close_all()
        OwnedPokemon.flush_cached_instance(self.mon)
        FieldMedicineUse._refresh(self.mon, self.snapshot()["pokemon"])
        self.assert_training(before, trained, item)
        runtime = build_battle_pokemon_from_model(self.mon)
        self.assertEqual(runtime.ivs, before["pokemon"]["ivs"])
        self.assertEqual(vars(runtime.base_stats), expected)
        self.assertEqual(runtime.max_hp, expected["hp"])
        payload = runtime.to_dict()
        restored = Pokemon.from_dict(payload)
        self.assertEqual(restored.ivs, before["pokemon"]["ivs"])
        self.assertEqual(vars(restored.base_stats), expected)
        legacy = dict(payload)
        legacy.pop("hyper_training")
        self.assertEqual(vars(Pokemon.from_dict(legacy).base_stats), expected)

    def test_gold_cap_player_flow(self):
        """One Gold Bottle Cap trains all eligible stats and preserves genetics."""
        self.flow()

    def test_genetically_perfect_or_already_trained_stats_do_not_spend(self):
        """Silver and Gold no-effect uses do not set useless markers or debit."""
        for ivs, flags in (([31] * 6, ["ordinary-hyper-fixture"]),
                           ([0] * 6, ["hypertrained:" + stat for stat in STATS])):
            self.prepare(ivs=ivs, flags=flags)
            for item in ITEMS:
                self.give(item)
                for stat in STATS if item == "Bottle Cap" else (None,):
                    before = self.snapshot()
                    self.record("terminal-no-effect", item + "=3" + ("/" + stat if stat else ""))
                    self.assertEqual(self.snapshot(), before)

    def test_gold_skips_perfect_and_prior_trained_stats(self):
        """The all-stat set is precisely the remaining effective-IV deficits."""
        self.prepare(ivs=[31, 0, 1, 2, 31, 3], flags=["other", "hypertrained:defense"])
        self.give("Gold Bottle Cap", 2)
        before = self.snapshot()
        self.record("gold-mixed-eligibility", "Gold Bottle Cap=3")
        self.assert_training(before, ["attack", "special_attack", "speed"], "Gold Bottle Cap", 1)
        before = self.snapshot()
        self.command("Gold Bottle Cap=3")
        self.assertEqual(self.snapshot(), before)

    def test_level_threshold_and_fresh_saved_level_exp(self):
        """Use actual production EXP/level changes and reject stale/corrupt data."""
        for item in ITEMS:
            self.give(item, 3)
            args = item + "=3" + ("/Atk" if item == "Bottle Cap" else "")
            for level in (49, 1):
                self.mon.set_level(level)
                self.mon.save(update_fields=["level", "total_exp"])
                self.prepare()
                before = self.snapshot()
                self.command(args)
                self.assertEqual(self.snapshot(), before)
                self.assertIn("level 50", self.player.messages[-1])
            self.mon.set_level(50)
            self.mon.save(update_fields=["level", "total_exp"])

            self.prepare()
            self.command(args)
            self.assertEqual(self.trainer.get_item_quantity(item), 2)
            self.prepare()
            self.state(level=50, total_exp=1)
            before = self.snapshot()
            self.command(args)
            self.assertEqual(self.snapshot(), before)
            self.assertIn("level/EXP", self.player.messages[-1])
            self.mon.set_level(50)
            self.mon.save(update_fields=["level", "total_exp"])

    def test_transformed_targets_reject_without_consumption(self):
        """A transient transformed holder cannot train its copied identity."""
        self.prepare()
        current = self.reload()
        current.transformed = True
        try:
            for item in ITEMS:
                self.give(item)
                before = self.snapshot()
                self.record("transformed-target", item + "=3" + ("/HP" if item == "Bottle Cap" else ""))
                self.assertEqual(self.snapshot(), before)
                self.assertIn("native field species", self.player.messages[-1])
        finally:
            del current.transformed

    def test_invalid_stat_missing_selector_and_gold_selectors_are_free(self):
        """Require exact stat names rather than move names, indexes or prefixes."""
        self.prepare()
        for item in ITEMS:
            self.give(item)
        for args in ("Bottle Cap", "Bottle Cap=3", "Bottle Cap=3/", "Bottle Cap=3/1",
                     "Bottle Cap=3/0", "Bottle Cap=3/sp", "Bottle Cap=3/Water Gun",
                     "Bottle Cap=3/all", "Gold Bottle Cap=3/all", "Gold Bottle Cap=3/HP",
                     "Bottle Cap=party/HP", "Bottle Cap=/HP", "Bottle Cap=Gold Bottle Cap"):
            before = self.snapshot()
            self.command(args)
            self.assertEqual(self.snapshot(), before)

    def test_exact_stat_aliases_item_and_inventory_normalization(self):
        """Full stat names and published aliases retain canonical mapping."""
        aliases = {"HP": "hp", "Attack": "attack", "DEFENCE": "defense", "SpAtk": "special_attack",
                   "Special Defense": "special_defense", "Speed": "speed", "SpA": "special_attack", "SpDef": "special_defense"}
        for alias, stat in aliases.items():
            self.prepare()
            InventoryEntry.objects.create(owner=self.trainer, item_name="BOTTLE CAP", quantity=1)
            self.record("normalized-bag-and-stat", "BOTTLE-CAP=" + str(self.mon.pk) + "/" + alias)
            self.assertEqual(HyperTraining.trained(self.mon), [stat])
            self.assertEqual(self.trainer.get_item_quantity("Bottle Cap"), 0)
        for args in ("Bottle=3/HP", "Gold Bottle=3"):
            before = self.snapshot()
            self.command(args)
            self.assertEqual(self.snapshot(), before)

    def test_invalid_saved_ivs_evs_flags_and_species_reject_without_repair(self):
        """Do not allow invalid saved data to reach fallback/random stat helpers."""
        for fields in ({"ivs": []}, {"ivs": [0] * 5}, {"ivs": [32] * 6},
                       {"evs": [253, 0, 0, 0, 0, 0]}, {"evs": [252, 252, 7, 0, 0, 0]},
                       {"flags": ["hypertrained:banana"]}, {"species": "Missing Species"},
                       {"species": "Gengar-Mega"}):
            for item in ITEMS:
                self.state(species="Eevee", evs=[0] * 6)
                self.prepare()
                self.state(**fields)
                self.give(item)
                before = self.snapshot()
                self.record("invalid-saved-hyper-target", item + "=3" + ("/HP" if item == "Bottle Cap" else ""))
                self.assertEqual(self.snapshot(), before, (fields, item))

    def test_fainted_hp_deficit_full_health_and_non_hp_training(self):
        """Use the field EV convention; changing effective IVs never revives."""
        for item, selector in (("Bottle Cap", "/HP"), ("Bottle Cap", "/Atk"), ("Gold Bottle Cap", "")):
            for hp in (0, 1, None):
                self.prepare(hp=hp)
                old_max = get_max_hp(self.mon)
                old_hp = self.snapshot()["pokemon"]["current_hp"]
                self.give(item)
                self.command(item + "=3" + selector)
                expected = 0 if hp == 0 else old_hp + get_max_hp(self.mon) - old_max
                self.assertEqual(self.snapshot()["pokemon"]["current_hp"], expected)
                self.assertEqual(self.snapshot()["pokemon"]["status"], "psn")
            self.prepare()
            self.state(current_hp=get_max_hp(self.mon))
            self.give(item)
            self.command(item + "=3" + selector)
            self.assertEqual(self.snapshot()["pokemon"]["current_hp"], get_max_hp(self.mon))

    def test_useful_training_can_precede_displayed_stat_rounding(self):
        """An effective-IV change remains useful when level-50 rounding hides it."""
        self.prepare(ivs=[30] * 6)
        stats = get_stats(self.mon)
        self.give("Bottle Cap")
        self.record("sub-stat-rounding", "Bottle Cap=3/Atk")
        self.assertEqual(get_stats(self.mon)["attack"], stats["attack"])
        self.assertEqual(HyperTraining.trained(self.mon), ["attack"])
        self.assertEqual(self.snapshot()["pokemon"]["ivs"], [30] * 6)
        self.assertEqual(self.trainer.get_item_quantity("Bottle Cap"), 0)

    def test_current_fusion_name_full_id_and_target_first(self):
        """Share the normal canonical field target syntax without compacting slots."""
        PlacementService(self.storage).reserve_for_fusion(self.mon)
        self.character.db.fusion_id = str(self.mon.pk)
        for item in ITEMS:
            for alias in ("fusion", "self", "me"):
                self.prepare()
                self.give(item)
                self.record("current-fusion-hyper-training", item + "=" + alias + ("/HP" if item == "Bottle Cap" else ""))
                self.assertEqual(self.trainer.get_item_quantity(item), 0)
        PlacementService(self.storage).return_from_fusion(self.mon, preferred_slot=3)
        self.character.db.fusion_id = None
        for args in ("Bottle Cap=Eevee/Atk", "Bottle Cap=" + str(self.mon.pk) + "/Def", "3=Gold Bottle Cap"):
            self.prepare()
            item = "Gold Bottle Cap" if args.startswith("3=") else "Bottle Cap"
            self.give(item)
            self.command(args)
            self.assertEqual(self.trainer.get_item_quantity(item), 0)

    def test_egg_box_and_inactive_fusion_guards(self):
        """Actual deposit/reservation paths make old field targets ineligible."""
        for item in ITEMS:
            self.prepare()
            self.give(item)
            suffix = "/Atk" if item == "Bottle Cap" else ""
            self.state(is_egg=True)
            before = self.snapshot()
            self.command(item + "=3" + suffix)
            self.assertEqual(self.snapshot(), before)
            self.state(is_egg=False)
            self.assertIn("deposited", self.command(str(self.mon.pk), "deposit"))
            before = self.snapshot()
            self.record("post-deposit-rejection", item + "=" + str(self.mon.pk) + suffix)
            self.assertEqual(self.snapshot(), before)
            PlacementService(self.storage).to_party(self.mon, slot=3)
            PlacementService(self.storage).reserve_for_fusion(self.mon)
            before = self.snapshot()
            self.command(item + "=fusion" + suffix)
            self.command(item + "=" + str(self.mon.pk) + suffix)
            self.assertEqual(self.snapshot(), before)
            PlacementService(self.storage).return_from_fusion(self.mon, preferred_slot=3)

    def test_ambiguous_foreign_gapped_and_changed_owner_targets(self):
        """Fresh placement and ownership always win over name/cache hints."""
        self.create_mon(slot=6)
        other = ObjectDB.objects.create(db_key="hyper-foreign-" + uuid4().hex)
        trainer = Trainer.objects.create(user=other, trainer_number=Trainer.objects.count() + 1)
        foreign = create_owned_pokemon("Eevee", trainer, 50)
        self.prepare()
        for item in ITEMS:
            self.give(item)
            for target in ("Eevee", "1", str(foreign.pk), "Missing"):
                before = self.snapshot()
                self.command(item + "=" + target + ("/HP" if item == "Bottle Cap" else ""))
                self.assertEqual(self.snapshot(), before)
        self.state(trainer_id=trainer.pk)
        for item in ITEMS:
            before = self.snapshot()
            self.command(item + "=3" + ("/HP" if item == "Bottle Cap" else ""))
            self.assertEqual(self.snapshot(), before)

    def test_missing_stock_and_battle_locks(self):
        """Both command and shared service guards protect real stock/effects."""
        self.prepare()
        for item in ITEMS:
            args = item + "=3" + ("/HP" if item == "Bottle Cap" else "")
            before = self.snapshot()
            self.command(args)
            self.assertEqual(self.snapshot(), before)
            self.give(item)
            before = self.snapshot()
            self.character.db.battle_lock = "hyper-training-fixture"
            self.command(args)
            self.assertIsNone(FieldHyperTrainingUse(self.player).use(item, "3", move="HP" if item == "Bottle Cap" else None))
            self.assertEqual(self.snapshot(), before)
            self.character.db.battle_lock = None
            self.player.ndb.battle_instance = object()
            self.command(args)
            self.assertEqual(self.snapshot(), before)
            self.player.ndb.battle_instance = None

    def test_failed_or_partial_debit_rolls_back_training_hp_and_bag(self):
        """Even a real debit followed by false cannot leak flags or HP."""
        original = Trainer.remove_item

        def partial(trainer, *args):
            """Fail after actual inventory SQL."""
            original(trainer, *args)
            return False

        for item in ITEMS:
            for debit in (lambda *args: False, partial):
                self.prepare()
                self.give(item)
                before = self.snapshot()
                with patch.object(Trainer, "remove_item", debit):
                    self.record("failed-hyper-debit", item + "=3" + ("/HP" if item == "Bottle Cap" else ""))
                self.assertEqual(self.snapshot(), before)

    def test_exception_after_actual_save_rolls_back_and_restores_cache(self):
        """The real flags/HP UPDATE and debit are both undone on a later fault."""
        original = OwnedPokemon.save

        def fail_after_save(pokemon, *args, **kwargs):
            """Preserve real SQL writes before injecting the exception."""
            original(pokemon, *args, **kwargs)
            raise RuntimeError("injected Hyper Training save failure")

        for item in ITEMS:
            self.prepare()
            self.give(item)
            before = self.snapshot()
            stats = get_stats(self.mon)
            with patch.object(OwnedPokemon, "save", fail_after_save):
                with self.assertRaisesRegex(RuntimeError, "injected Hyper"):
                    self.command(item + "=3" + ("/HP" if item == "Bottle Cap" else ""))
            self.assertEqual(self.snapshot(), before)
            self.assertEqual(get_stats(self.mon), stats)
            self.assertEqual(self.mon.flags, before["pokemon"]["flags"])

    def test_parent_transaction_rollback_has_no_training_cache_or_notice(self):
        """Reuse progression's commit-aware copies and robust notification boundary."""
        from django.db import transaction
        self.prepare()
        self.give("Gold Bottle Cap")
        before = self.snapshot()
        start = len(self.player.messages)
        with self.assertRaisesRegex(RuntimeError, "rollback parent"):
            with transaction.atomic():
                self.command("Gold Bottle Cap=3")
                self.assertEqual(self.mon.flags, before["pokemon"]["flags"])
                self.assertEqual(self.player.messages[start:], [])
                raise RuntimeError("rollback parent")
        self.assertEqual(self.snapshot(), before)

    def race(self, *actions):
        """Synchronize independent PostgreSQL connections before real commands."""
        from django.db import close_old_connections
        barrier = Barrier(len(actions))

        def run(action):
            """Release each worker's connection even when an assertion fails."""
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return action()
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            return list(pool.map(run, actions))

    def test_last_copy_each_cap_has_one_effect(self):
        """The final copy cannot fund two different stat requests or Gold uses."""
        for item in ITEMS:
            self.prepare()
            self.give(item)
            left = item + "=3" + ("/HP" if item == "Bottle Cap" else "")
            right = item + "=3" + ("/Atk" if item == "Bottle Cap" else "")
            self.race(lambda: self.command(left), lambda: self.command(right))
            trained = HyperTraining.trained(self.reload())
            self.assertEqual(len(trained), 1 if item == "Bottle Cap" else 6)
            self.assertEqual(self.trainer.get_item_quantity(item), 0)
            self.assertEqual(self.snapshot()["pokemon"]["ivs"], [0, 1, 2, 3, 4, 5])

    def test_last_copy_cannot_train_two_different_targets(self):
        """All owned targets share the same locked inventory budget."""
        other = self.create_mon(slot=6)
        for item in ITEMS:
            self.prepare()
            self.state(other, flags=[])
            self.give(item)
            suffix = "/HP" if item == "Bottle Cap" else ""
            self.race(lambda: self.command(item + "=3" + suffix), lambda: self.command(item + "=6" + suffix))
            rows = [self.snapshot(pokemon)["pokemon"] for pokemon in (self.mon, other)]
            self.assertEqual(sum(any(flag.startswith("hypertrained:") for flag in row["flags"]) for row in rows), 1)
            self.assertEqual(self.trainer.get_item_quantity(item), 0)

    def test_competing_duplicate_and_distinct_stat_uses_recheck_fresh_flags(self):
        """Duplicates spend once; different stat requests safely merge their flags."""
        self.prepare()
        self.give("Bottle Cap", 4)
        self.race(lambda: self.command("Bottle Cap=3/HP"), lambda: self.command("Bottle Cap=3/HP"))
        self.assertEqual(self.trainer.get_item_quantity("Bottle Cap"), 3)
        self.race(lambda: self.command("Bottle Cap=3/Atk"), lambda: self.command("Bottle Cap=3/Def"))
        self.assertEqual(self.trainer.get_item_quantity("Bottle Cap"), 1)
        self.assertEqual(set(self.snapshot()["pokemon"]["flags"]),
                         {"ordinary-hyper-fixture", "hypertrained:hp", "hypertrained:attack", "hypertrained:defense"})
        self.assertEqual(HyperTraining.trained(self.reload()), ["hp", "attack", "defense"])

    def test_gold_and_single_cap_contention_preserves_eligible_set(self):
        """Gold-first keeps the single cap; single-first leaves Gold only the rest."""
        self.prepare()
        before = self.snapshot()["pokemon"]
        old_max = get_max_hp(self.mon)
        for item in ITEMS:
            self.give(item)
        retained = self.mon
        self.race(lambda: self.command("Gold Bottle Cap=3"), lambda: self.command("Bottle Cap=3/HP"))
        self.assert_committed_caps(before, old_max, retained)
        self.assertEqual(self.trainer.get_item_quantity("Gold Bottle Cap"), 0)
        self.assertIn(self.trainer.get_item_quantity("Bottle Cap"), (0, 1))

    def assert_committed_caps(self, before, old_max, retained):
        """Check committed SQL and fresh models; retained objects are diagnostic only."""
        row = self.snapshot()["pokemon"]
        expected = {"ordinary-hyper-fixture", *("hypertrained:" + stat for stat in STATS)}
        self.assertEqual(set(row["flags"]), expected)
        self.assertEqual(HyperTraining.trained(self.reload()), list(STATS))
        self.assertEqual(self.mon.flags, row["flags"])
        for key, value in before.items():
            if key not in {"flags", "current_hp"}:
                self.assertEqual(row[key], value, key)
        self.assertEqual(row["ivs"], [0, 1, 2, 3, 4, 5])
        self.assertEqual(row["current_hp"], before["current_hp"] + get_max_hp(self.mon) - old_max)
        EVIDENCE.append({"label": "committed-cap-contention", "test": self.id(),
                         "retained_flags": list(retained.flags), "sql_flags": row["flags"],
                         "reloaded_flags": list(self.mon.flags), "genetic_ivs": row["ivs"],
                         "hp_before": before["current_hp"], "hp_after": row["current_hp"],
                         "gold_remaining": self.trainer.get_item_quantity("Gold Bottle Cap"),
                         "single_remaining": self.trainer.get_item_quantity("Bottle Cap")})

    def cap_serial_order(self, gold_first):
        """Exercise each legal order explicitly with exact debits and committed flags."""
        self.prepare()
        before = self.snapshot()["pokemon"]
        old_max = get_max_hp(self.mon)
        for item in ITEMS:
            self.give(item)
        retained = self.mon
        inputs = ("Gold Bottle Cap=3", "Bottle Cap=3/HP")
        for args in inputs if gold_first else reversed(inputs):
            self.command(args)
        self.assert_committed_caps(before, old_max, retained)
        self.assertEqual(self.trainer.get_item_quantity("Gold Bottle Cap"), 0)
        self.assertEqual(self.trainer.get_item_quantity("Bottle Cap"), int(gold_first))

    def test_gold_then_single_cap_serialized(self):
        """A committed Gold use leaves a later no-effect single cap untouched."""
        self.cap_serial_order(True)

    def test_single_then_gold_cap_serialized(self):
        """A committed single use lets Gold train the five remaining stats."""
        self.cap_serial_order(False)

    def test_evolution_ev_training_berry_and_healing_keep_overlay(self):
        """Use existing player routes after training without replacing genetics."""
        self.prepare()
        original = self.snapshot()["pokemon"]["ivs"]
        for item in ("Gold Bottle Cap", "Fire Stone", "HP Up", "Pomeg Berry", "Potion"):
            self.give(item)
        self.command("Gold Bottle Cap=3")
        self.command(str(self.mon.pk) + " Fire Stone", "evolve")
        self.assertEqual(self.snapshot()["pokemon"]["species"], "Flareon")
        self.command("HP Up=3")
        self.assertEqual(self.snapshot()["pokemon"]["evs"][0], 10)
        self.command("Pomeg Berry=3")
        self.assertEqual(self.snapshot()["pokemon"]["evs"][0], 0)
        self.state(current_hp=get_max_hp(self.mon) - 1)
        self.command("Potion=3")
        self.assertEqual(self.snapshot()["pokemon"]["current_hp"], get_max_hp(self.mon))
        self.assertEqual(self.snapshot()["pokemon"]["ivs"], original)
        self.assertEqual(HyperTraining.trained(self.mon), list(STATS))

    def test_runtime_session_checkpoint_rebuild_keeps_training_and_genetics(self):
        """Start/rebuild the production battle session after the ordinary field route."""
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle.engine import BattleType
        from pokemon.battle.handler import battle_handler
        from pokemon.battle.pokemon_factory import create_battle_pokemon

        self.prepare()
        self.give("Gold Bottle Cap")
        self.command("Gold Bottle Cap=3")
        expected = get_stats(self.mon)
        room = ObjectDB.objects.create(db_key="hyper-room-" + uuid4().hex)
        self.player.location = SimpleNamespace(pk=room.pk, id=room.pk, key=room.key,
                                              db=room.db, ndb=room.ndb, attributes=room.attributes, contents=[self.player])
        session = BattleSession(self.player)
        foe = create_battle_pokemon("Magikarp", 50, is_wild=True, move_names=["Splash"])
        session._track_temp_opponent_team([foe])
        session._select_opponent = lambda: (foe, "Fixture Magikarp", BattleType.WILD, "Fixture encounter")
        with patch("pokemon.battle.battleinstance.search_object", lambda query: [self.player] if query == f"#{self.player.id}" else []):
            try:
                session.start()
                for _ in range(2):
                    runtime = session.battle.participants[0].active[0]
                    self.assertEqual(vars(runtime.base_stats), expected)
                    self.assertEqual(runtime.ivs, self.snapshot()["pokemon"]["ivs"])
                    self.assertEqual(runtime.hyper_training, list(STATS))
                    session._sync_active_battle_state()
                    session._persist_turn_state()
                    identifier = session.battle_id
                    battle_handler.unregister(session)
                    self.player.ndb.battle_instance = None
                    self.player.location.ndb.battle_instances = {}
                    session = BattleSession.restore(self.player.location, identifier)
                    self.assertIsNotNone(session)
                EVIDENCE.append({"label": "normal-session-rebuild", "rebuilds": 2,
                                 "genetic_ivs": self.snapshot()["pokemon"]["ivs"], "stats": expected})
            finally:
                if session:
                    session.end()


STATS = ("hp", "attack", "defense", "special_attack", "special_defense", "speed")
LABELS = ("HP", "Atk", "Def", "SpA", "SpD", "Spe")
ITEMS = ("Bottle Cap", "Gold Bottle Cap")


def add_flow(stat):
    """Count the ordinary selected-stat flow separately for each mapping."""
    def case(self):
        """Run one stat's actual discover/use/SQL/runtime reload flow."""
        self.flow(stat)
    setattr(HyperTrainingCases, "test_bottle_cap_player_flow_" + stat, case)


for trained_stat in STATS:
    add_flow(trained_stat)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from evennia.commands.command import Command
        from evennia.commands.cmdset import CmdSet
        with patch.object(evennia, "Command", Command), patch.object(evennia, "CmdSet", CmdSet):
            from evennia.utils.evmenu import CmdEvMenuNode
            from utils.enhanced_evmenu import EnhancedEvMenu
            from commands.player.cmd_inventory import CmdInventory, CmdUseItem
            from commands.player.cmd_party import CmdDepositPokemon, CmdSetHoldItem
            from commands.player.cmd_sheet import CmdSheetPokemon
            from commands.player.cmd_learn_evolve import CmdEvolvePokemon
            from commands.player.cmd_pokedex import CmdItemdexSearch
        from evennia.objects.models import ObjectDB
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon, get_max_hp, get_stats
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot, MovePPBoost, MovesetSlot, PokemonLearnedMove
        from pokemon.models.storage import PokemonPlacement, StorageBox, UserStorage
        from pokemon.models.trainer import Trainer, InventoryEntry
        from pokemon.services.field_items import FieldMedicineUse
        from pokemon.services.field_hyper_training import FieldHyperTrainingUse
        from pokemon.services.placement import PlacementService
        from pokemon.hyper_training import HyperTraining
        from pokemon.battle.battledata import Pokemon
        from pokemon.user import User
        COMMANDS = {"use": CmdUseItem, "inventory": CmdInventory, "party": CmdSheetPokemon,
                    "deposit": CmdDepositPokemon, "hold": CmdSetHoldItem,
                    "evolve": CmdEvolvePokemon, "itemdex": CmdItemdexSearch}
        try:
            result = unittest.main(verbosity=2, exit=False).result
        finally:
            destination = os.environ.get("PF2_HYPER_TRAINING_EVIDENCE")
            if destination:
                Path(destination).write_text(json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())

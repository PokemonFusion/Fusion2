"""Acquire and use the two field equivalents through real commands and SQL."""

import json
import os
from pathlib import Path
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import item_availability_cases as acquisition

EVIDENCE = []


class RecoveryEquivalentCases(unittest.TestCase):
    """Share existing acquisition transports, never substitute the medicine effects."""

    setUp = acquisition.AcquisitionCases.setUp
    tearDown = acquisition.AcquisitionCases.tearDown
    native = acquisition.AcquisitionCases.native
    state = acquisition.AcquisitionCases.state
    command = acquisition.AcquisitionCases.command
    reply = acquisition.AcquisitionCases.reply
    buy = acquisition.AcquisitionCases.buy

    def prepare(self, item):
        """Give each item a useful real saved target, with gapped PP slots."""
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=12, status="slp", sleep_turns=2,
            friendship=137, held_item=item)
        self.mon.activemoveslot_set.filter(slot=2).update(slot=4)
        ActiveMoveslot.objects.filter(pokemon=self.mon).update(current_pp=1)

    def flow(self, item, selector):
        """Buy from empty stock, discover, apply, and reload with exact durable effect."""
        self.prepare(item)
        self.buy(item, price=350 if item == "Rage Candy Bar" else 300)
        self.assertIn("Field use", self.command("itemdex", item))
        before = self.state()
        self.command("use", item + "=3" + selector)
        self.assertEqual(self.player.trainer.get_item_quantity(item), 0)
        row = OwnedPokemon.objects.filter(pk=self.mon.pk).values().get()
        self.assertEqual(row["held_item"], item)
        self.assertEqual(row["current_hp"], 12)
        if item == "Rage Candy Bar":
            self.assertEqual((row["status"], row["sleep_turns"]), ("", None))
        else:
            self.assertEqual(ActiveMoveslot.objects.get(pokemon=self.mon, slot=4).current_pp, 11)
            self.assertEqual(row["status"], "slp")
        from django.db import connections
        connections.close_all()
        OwnedPokemon.flush_cached_instance(self.mon)
        self.assertEqual(OwnedPokemon.objects.get(pk=self.mon.pk).held_item, item)
        EVIDENCE.append({"label": "ordinary-recovery-equivalent", "item": item, "before": before,
            "after": self.state(), "commands": ["+store", "1", item + " 1", "+itemdex " + item,
                "+use " + item + "=3" + selector, "SQL reload"], "messages": list(map(str, self.player.messages))})

    def test_rage_candy_purchase_use_reload(self):
        """The modern status cure is medicinal, without a story or HP grant."""
        self.flow("Rage Candy Bar", "")

    def test_hopo_purchase_selected_move_use_reload(self):
        """One selected move receives ten PP without spending its held copy."""
        self.flow("Hopo Berry", "/Water Gun")

    def test_all_major_statuses_and_no_effect_fainted_guards(self):
        """Every major cure clears durable counters; no effect consumes nothing."""
        for status in ("psn", "tox", "brn", "par", "slp", "frz", ""):
            self.player.trainer.add_item("Rage Candy Bar")
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(status=status, current_hp=12, sleep_turns=2)
            before = self.player.trainer.get_item_quantity("Rage Candy Bar")
            self.command("use", "Rage Candy Bar=3")
            self.assertEqual(self.player.trainer.get_item_quantity("Rage Candy Bar"), before - bool(status))
            self.assertEqual(OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("status", flat=True).get(), "")
        for item in ("Rage Candy Bar", "Hopo Berry"):
            self.prepare(item)
            self.player.trainer.add_item(item)
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=0)
            before = self.state()
            self.command("use", item + "=3" + ("/4" if item == "Hopo Berry" else ""))
            self.assertEqual(self.state(), before)

    def test_hopo_exact_slot_names_boosted_cap_and_no_effect(self):
        """Actual slot4 works; missing/gapped/ambiguous inputs never select another move."""
        self.prepare("Hopo Berry")
        slot = ActiveMoveslot.objects.get(pokemon=self.mon, slot=4)
        MovePPBoost.objects.create(pokemon=self.mon, move=slot.move, bonus_pp=15)
        maximum = self.mon.get_max_pp(slot.move.name)
        slot.current_pp = maximum - 3
        slot.save()
        self.player.trainer.add_item("Hopo Berry", 2)
        for selector in ("", "/2", "/Water", "/No Such Move"):
            before = self.state()
            self.command("use", "Hopo Berry=3" + selector)
            self.assertEqual(self.state(), before)
        self.command("use", "Hopo Berry=3/4")
        self.assertEqual(ActiveMoveslot.objects.get(pk=slot.pk).current_pp, maximum)
        self.assertEqual(self.player.trainer.get_item_quantity("Hopo Berry"), 1)
        before = self.state()
        self.command("use", "Hopo Berry=3/Water Gun")
        self.assertEqual(self.state(), before)

    def test_fresh_egg_box_foreign_battle_and_held_only_guards(self):
        """Both additions reuse current canonical target and independent bag eligibility."""
        for item in ("Rage Candy Bar", "Hopo Berry"):
            self.prepare(item)
            before = self.state()
            suffix = "/4" if item == "Hopo Berry" else ""
            self.command("use", item + "=3" + suffix)
            self.assertEqual(self.state(), before)
            self.player.trainer.add_item(item)
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(is_egg=True)
            before = self.state()
            self.command("use", item + "=3" + suffix)
            self.assertEqual(self.state(), before)
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(is_egg=False)
            self.player.db.battle_lock = True
            before = self.state()
            self.command("use", item + "=3" + suffix)
            self.assertEqual(self.state(), before)
            self.player.db.battle_lock = False
            self.command("use", item + "=3" + suffix, side=1)
            self.assertEqual(self.state(), before)
        PlacementService(self.player.storage).to_box(self.mon)
        before = self.state()
        self.command("use", "Hopo Berry=3/4")
        self.assertEqual(self.state(), before)

    def test_partial_debit_and_post_effect_write_faults_roll_back(self):
        """Real effect/debit SQL is undone together for status and PP paths."""
        for item, model in (("Rage Candy Bar", OwnedPokemon), ("Hopo Berry", ActiveMoveslot)):
            self.prepare(item)
            self.player.trainer.add_item(item)
            suffix = "/4" if item == "Hopo Berry" else ""
            before = self.state()
            original_remove, original_save = Trainer.remove_item, model.save

            def partial(trainer, *args):
                """Fail after real bag SQL."""
                original_remove(trainer, *args)
                return False

            def post_save(target, *args, **kwargs):
                """Fail after the real HP/status or PP save."""
                original_save(target, *args, **kwargs)
                raise RuntimeError("recovery post-save fixture")

            for target, attr, failure in ((Trainer, "remove_item", partial), (model, "save", post_save)):
                with patch.object(target, attr, failure):
                    try:
                        self.command("use", item + "=3" + suffix)
                    except RuntimeError:
                        pass
                self.assertEqual(self.state(), before)

    def test_current_fusion_and_ambiguous_or_stale_targets(self):
        """Both items share canonical Fusion checks and reject duplicate-name guesses."""
        other = self.native("Mew", 6)
        for item in ("Rage Candy Bar", "Hopo Berry"):
            self.prepare(item)
            self.player.trainer.add_item(item)
            before = self.state()
            self.command("use", item + "=Mew" + ("/4" if item == "Hopo Berry" else ""))
            self.assertEqual(self.state(), before)
        PlacementService(self.player.storage).to_box(other)
        PlacementService(self.player.storage).reserve_for_fusion(self.mon)
        self.player.db.fusion_id = str(self.mon.pk)
        for item in ("Rage Candy Bar", "Hopo Berry"):
            self.prepare(item)
            self.command("use", item + "=fusion" + ("/4" if item == "Hopo Berry" else ""))
            self.assertEqual(self.player.trainer.get_item_quantity(item), 0)

    def test_final_copy_contention_has_one_effect(self):
        """Independent connections recheck bag and target state inside shared field locks."""
        from django.db import close_old_connections

        for item in ("Rage Candy Bar", "Hopo Berry"):
            self.prepare(item)
            self.player.trainer.add_item(item)
            barrier = Barrier(2)

            def run(_):
                """Use the real command after synchronizing database workers."""
                close_old_connections()
                try:
                    barrier.wait(timeout=10)
                    self.command("use", item + "=3" + ("/4" if item == "Hopo Berry" else ""))
                finally:
                    close_old_connections()

            with ThreadPoolExecutor(max_workers=2) as pool:
                list(pool.map(run, range(2)))
            self.assertEqual(self.player.trainer.get_item_quantity(item), 0)
            if item == "Hopo Berry":
                self.assertEqual(ActiveMoveslot.objects.get(pokemon=self.mon, slot=4).current_pp, 11)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        acquisition.load_runtime()
        import evennia
        from evennia.commands.command import Command
        with patch.object(evennia, "Command", Command):
            from commands.player import cmd_pokedex
        acquisition.COMMANDS["itemdex"] = (cmd_pokedex, cmd_pokedex.CmdItemdexSearch)
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot, MovePPBoost
        from pokemon.models.trainer import Trainer
        from pokemon.services.placement import PlacementService

        try:
            result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RecoveryEquivalentCases))
        finally:
            if os.environ.get("PF2_RECOVERY_EQUIVALENT_EVIDENCE"):
                Path(os.environ["PF2_RECOVERY_EQUIVALENT_EVIDENCE"]).write_text(json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())

"""Real coin purchase, evolution, failure and contention on disposable SQL."""

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


class GimmighoulCoinCases(unittest.TestCase):
    """Keep normal parser/menu/SQL behavior while adapting only player transport."""

    tearDown = acquisition.AcquisitionCases.tearDown
    native = acquisition.AcquisitionCases.native
    state = acquisition.AcquisitionCases.state
    command = acquisition.AcquisitionCases.command
    reply = acquisition.AcquisitionCases.reply

    def setUp(self):
        """Create one ordinary Chest holder in a genuinely gapped party."""
        acquisition.AcquisitionCases.setUp(self)
        PlacementService(self.player.storage).to_box(self.mon)
        self.mon = self.native("Gimmighoul", 3)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(nickname="Coin Buddy", held_item="Leftovers",
            current_hp=3, status="slp", sleep_turns=2, friendship=137, flags=["coin-fixture"])

    def row(self):
        """Bypass the identity map for every committed-state assertion."""
        return OwnedPokemon.objects.filter(pk=self.mon.pk).values().get()

    def evolve(self, target="", pokemon=None):
        """Use the shipped complete-ID command with an actual coin item argument."""
        return self.command("evolve", str((pokemon or self.mon).pk) + " Gimmighoul Coin" + target)

    def quantity(self):
        """Count normalized coin inventory, never character prose or held copies."""
        return self.player.trainer.get_item_quantity("Gimmighoul Coin")

    def test_purchase_discover_evolve_reload_and_retry(self):
        """Acquire all 999 copies from the real menu before using the normal route."""
        self.room.db.store_inventory = {"Gimmighoul Coin": {"price": 10, "quantity": 1000}}
        before = self.state()
        self.command("store")
        for text in ("1", "Gimmighoul Coin 999", "back", "q"):
            self.reply(text)
        self.assertEqual(self.quantity(), 999)
        self.assertIn("Gimmighoul Coin", self.command("inventory"))
        self.assertIn("999", self.command("itemdex", "Gimmighoul Coin"))
        self.assertIn(str(self.mon.pk), self.command("party", "3"))
        before_evolution = self.row()
        output = self.evolve()
        self.assertIn("evolved into Gholdengo", output)
        self.assertEqual(self.quantity(), 0)
        self.assertEqual(self.row()["ability"], "Good as Gold")
        self.assertEqual(list(OwnedPokemon.objects.get(pk=self.mon.pk).types), ["Steel", "Ghost"])
        for key, value in before_evolution.items():
            if key not in {"species", "ability", "type_", "flags"}:
                self.assertEqual(self.row()[key], value, key)
        self.assertIn("coin-fixture", self.row()["flags"])
        from django.db import connections
        connections.close_all()
        OwnedPokemon.flush_cached_instance(self.mon)
        self.mon = OwnedPokemon.objects.get(pk=self.mon.pk)
        self.assertEqual(self.mon.species, "Gholdengo")
        after = self.state()
        self.evolve()
        self.assertEqual(self.state(), after)
        self.assertEqual(after["wallet"], before["wallet"] - 9990)
        self.assertEqual(after["stock"]["Gimmighoul Coin"]["quantity"], 1)
        EVIDENCE.append({"label": "ordinary-coin-purchase-evolve-reload", "before": before,
                         "after": after, "messages": list(map(str, self.player.messages))})

    def test_insufficient_and_held_only_coins_do_not_qualify(self):
        """0/998 bag copies and a held coin cannot pay for the 999-unit requirement."""
        for quantity in (0, 998):
            if quantity:
                self.player.trainer.add_item("Gimmighoul Coin", quantity)
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(held_item="Gimmighoul Coin")
            before = self.state()
            self.evolve()
            self.assertEqual(self.state(), before)

    def test_one_thousand_leaves_exactly_one(self):
        """The large debit is exact, not one item or all available coins."""
        self.player.trainer.add_item("Gimmighoul Coin", 1000)
        self.evolve()
        self.assertEqual(self.quantity(), 1)
        self.assertEqual(self.row()["species"], "Gholdengo")

    def boundary_level(self, level):
        """Apply the documented minimum/capped level with real EXP consistency."""
        from pokemon.models.stats import exp_for_level

        OwnedPokemon.objects.filter(pk=self.mon.pk).update(level=level, total_exp=exp_for_level(level, "medium_fast"))
        self.player.trainer.add_item("Gimmighoul Coin", 999)
        self.evolve()
        self.assertEqual((self.row()["species"], self.row()["level"]), ("Gholdengo", level))
        self.assertEqual(self.quantity(), 0)

    def test_minimum_level_two(self):
        """Level2 qualifies under the explicit PF2 manual timing equivalent."""
        self.boundary_level(2)

    def test_level_one_hundred(self):
        """The capped native target can explicitly evolve without gaining a level."""
        self.boundary_level(100)

    def test_wrong_target_everstone_egg_and_native_forms_fail(self):
        """Changes are checked from fresh SQL rather than a retained owned object."""
        self.player.trainer.add_item("Gimmighoul Coin", 999)
        original = self.row()
        for updates, target in (({}, "=Gimmighoul-Roaming"), ({"held_item": "Everstone"}, ""),
                ({"is_egg": True}, ""), ({"species": "Gimmighoul-Roaming", "ability": "Run Away"}, ""),
                ({"species": "Ditto", "nickname": "Gimmighoul"}, ""), ({"ability": "Run Away"}, ""),
                ({"level": 1}, ""), ({"total_exp": -1}, "")):
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(**{key: original[key] for key in
                ("species", "ability", "nickname", "held_item", "is_egg", "level", "total_exp")})
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(**updates)
            before = self.state()
            self.evolve(target)
            self.assertEqual(self.state(), before)

    def test_failed_partial_debit_preserves_species_coins_and_cache(self):
        """A false return after real quantity SQL rolls back the complete transition."""
        self.player.trainer.add_item("Gimmighoul Coin", 999)
        before = self.state()
        original = Trainer.remove_item

        def partial(trainer, *args):
            """Inject after actual normalized inventory debit."""
            original(trainer, *args)
            return False

        with patch.object(Trainer, "remove_item", partial):
            self.evolve()
        self.assertEqual(self.state(), before)
        self.assertEqual(self.mon.species, "Gimmighoul")

    def test_post_save_failure_restores_all_rows(self):
        """The real species/ability/receipt SQL cannot commit without its coin debit."""
        self.player.trainer.add_item("Gimmighoul Coin", 999)
        before = self.state()
        original = OwnedPokemon.save

        def fail_after_save(mon, *args, **kwargs):
            """Execute real transition persistence before failing."""
            original(mon, *args, **kwargs)
            raise RuntimeError("post-evolution fixture")

        with patch.object(OwnedPokemon, "save", fail_after_save):
            self.evolve()
        self.assertEqual(self.state(), before)
        self.assertEqual(self.mon.species, "Gimmighoul")

    def test_parent_rollback_keeps_native_cache_and_no_success_message(self):
        """A containing transaction cannot publish a temporary evolution."""
        from django.db import transaction

        self.player.trainer.add_item("Gimmighoul Coin", 999)
        before = self.state()
        self.player.messages.append("outer fixture begins")
        with self.assertRaisesRegex(RuntimeError, "outer evolution"):
            with transaction.atomic():
                self.evolve()
                self.assertFalse(any("evolved into" in str(text) for text in self.player.messages))
                raise RuntimeError("outer evolution")
        self.assertEqual(self.state(), before)
        self.assertEqual(self.mon.species, "Gimmighoul")

    def test_foreign_owner_battle_and_reserved_placement_fail(self):
        """The real shared lifecycle guards still control this new debit size."""
        self.player.trainer.add_item("Gimmighoul Coin", 999)
        before = self.state()
        self.command("evolve", str(self.mon.pk) + " Gimmighoul Coin", side=1)
        self.assertEqual(self.state(), before)
        self.player.db.battle_lock = True
        self.evolve()
        self.assertEqual(self.state(), before)
        self.player.db.battle_lock = False
        placement = PokemonPlacement.objects.get(pokemon=self.mon)
        PokemonPlacement.objects.filter(pk=placement.pk).update(location_type="fusion", slot=None)
        before = self.state()
        self.evolve()
        self.assertEqual(self.state(), before)

    def race(self, targets):
        """Submit real normal evolution commands on independent worker connections."""
        from django.db import close_old_connections

        barrier = Barrier(len(targets))

        def run(mon):
            """Ensure connection cleanup on either serialized outcome."""
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return self.evolve(pokemon=mon)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=len(targets)) as pool:
            return list(pool.map(run, targets))

    def test_concurrent_replay_spends_once(self):
        """Two completions cannot spend 1,998 coins on one transition."""
        self.player.trainer.add_item("Gimmighoul Coin", 1998)
        self.race([self.mon, self.mon])
        self.assertEqual(self.quantity(), 999)
        self.assertEqual(self.row()["species"], "Gholdengo")

    def test_two_targets_share_one_qualified_coin_budget(self):
        """One inventory cannot fund two different native Pokemon concurrently."""
        other = self.native("Gimmighoul", 6)
        self.player.trainer.add_item("Gimmighoul Coin", 999)
        self.race([self.mon, other])
        self.assertEqual(OwnedPokemon.objects.filter(pk__in=[self.mon.pk, other.pk], species="Gholdengo").count(), 1)
        self.assertEqual(self.quantity(), 0)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        acquisition.load_runtime()
        import evennia
        from evennia.commands.command import Command
        with patch.object(evennia, "Command", Command):
            from commands.player import cmd_pokedex, cmd_sheet
        acquisition.COMMANDS["itemdex"] = (cmd_pokedex, cmd_pokedex.CmdItemdexSearch)
        acquisition.COMMANDS["party"] = (cmd_sheet, cmd_sheet.CmdSheetPokemon)
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.storage import PokemonPlacement
        from pokemon.models.trainer import Trainer
        from pokemon.services.placement import PlacementService

        try:
            result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(GimmighoulCoinCases))
        finally:
            if os.environ.get("PF2_COIN_EVIDENCE"):
                Path(os.environ["PF2_COIN_EVIDENCE"]).write_text(json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())

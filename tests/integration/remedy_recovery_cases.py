"""Four field-only medicines through ordinary inventory/use and guarded SQL."""

import json
import os
from pathlib import Path
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import item_availability_cases as acquisition
from recovery_equivalent_cases import RecoveryEquivalentCases


ITEMS = {"Remedy": (20, 5, 10, 150), "Fine Remedy": (60, 10, 15, 150),
         "Superb Remedy": (120, 15, 20, 750), "Jubilife Muffin": (0, 0, 0, 250)}
EVIDENCE = []


class RemedyRecoveryCases(RecoveryEquivalentCases):
    """Reuse normal transport/fixture setup, retaining independent row observations."""

    def prepare_new(self, item, *, hp=1, friendship=200):
        """Label injuries, major status and a separate physical held copy."""
        from pokemon.models.core import OwnedPokemon

        OwnedPokemon.objects.filter(pk=self.mon.pk).update(
            current_hp=hp, friendship=friendship, status="slp" if item == "Jubilife Muffin" else "psn",
            sleep_turns=2 if item == "Jubilife Muffin" else None, held_item=item)
        OwnedPokemon.flush_cached_instance(self.mon)

    def row(self):
        """Read canonical persisted fields instead of relying on a cached instance."""
        from pokemon.models.core import OwnedPokemon
        return OwnedPokemon.objects.filter(pk=self.mon.pk).values("current_hp", "status", "sleep_turns", "friendship", "held_item").get()

    def outcome(self, item, before):
        """Verify actual useful effect, tiered penalty and independent held conservation."""
        from pokemon.helpers.pokemon_helpers import get_max_hp
        from pokemon.models.core import OwnedPokemon

        amount, low, high, _ = ITEMS[item]
        after = self.row()
        if amount:
            maximum = get_max_hp(OwnedPokemon.objects.get(pk=self.mon.pk))
            self.assertEqual(after["current_hp"], min(maximum, before["current_hp"] + amount))
            self.assertEqual(after["status"], before["status"])
        else:
            self.assertEqual((after["current_hp"], after["status"], after["sleep_turns"]),
                             (before["current_hp"], "", None))
        self.assertEqual(after["friendship"], max(0, before["friendship"] - (high if before["friendship"] >= 200 else low)))
        self.assertEqual(after["held_item"], item)
        return after

    def flow_new(self, item):
        """Purchase, discover and use one bag copy, retaining a separate held copy."""
        from django.db import connections
        from pokemon.models.core import OwnedPokemon

        self.prepare_new(item)
        self.buy(item, price=ITEMS[item][3])
        self.assertIn("Field use", self.command("itemdex", item))
        self.command("inventory")
        before = self.row()
        self.command("use", item + "=3")
        self.assertEqual(self.player.trainer.get_item_quantity(item), 0)
        after = self.outcome(item, before)
        connections.close_all()
        OwnedPokemon.flush_cached_instance(self.mon)
        self.assertEqual(self.row(), after)
        EVIDENCE.append({"case": self.id(), "label": "ordinary-purchase-discovery-use-reconnect",
                         "item": item, "before": before, "after": after,
                         "limit": "Tagged finite shop/native target prerequisites; no public world stock claim",
                         "messages": list(map(str, self.player.messages))})

    def no_effect_new(self, item):
        """Fainted and fully healthy targets conserve both stock and friendship."""
        from pokemon.helpers.pokemon_helpers import get_max_hp
        from pokemon.models.core import OwnedPokemon

        self.player.trainer.add_item(item, 2)
        for hp in (0, get_max_hp(self.mon)):
            self.prepare_new(item, hp=hp)
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(status="", sleep_turns=None)
            before = self.row()
            self.command("use", item + "=3")
            self.assertEqual(self.row(), before)
            self.assertEqual(self.player.trainer.get_item_quantity(item), 2)

    def guards_new(self, item):
        """Reject eggs, battle locks, foreign owners, boxed/stale and held-only targets."""
        from pokemon.models.core import OwnedPokemon
        from pokemon.services.placement import PlacementService

        self.prepare_new(item)
        before = self.row()
        self.command("use", item + "=3")
        self.assertEqual(self.row(), before)
        self.player.trainer.add_item(item, 1)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(is_egg=True)
        before = self.state()
        self.command("use", item + "=3")
        self.assertEqual(self.state(), before)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(is_egg=False)
        self.player.db.battle_lock = True
        before = self.state()
        self.command("use", item + "=3")
        self.assertEqual(self.state(), before)
        self.player.db.battle_lock = False
        before = self.row()
        self.players[1].trainer.add_item(item, 1)
        self.command("use", item + "=" + str(self.mon.pk), side=1)
        self.assertEqual(self.row(), before)
        self.assertEqual(self.players[1].trainer.get_item_quantity(item), 1)
        PlacementService(self.player.storage).to_box(self.mon)
        before = self.row()
        self.command("use", item + "=" + str(self.mon.pk))
        self.command("use", item + "=3")
        self.assertEqual(self.row(), before)
        self.assertEqual(self.player.trainer.get_item_quantity(item), 1)

    def rollback_new(self, item):
        """A post-debit or post-owned-write fault cannot charge friendship or stock."""
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.trainer import Trainer

        self.prepare_new(item)
        self.player.trainer.add_item(item, 1)
        original_remove, original_save = Trainer.remove_item, OwnedPokemon.save

        def partial(trainer, *args):
            """Exercise the real debit before injecting a refused transaction."""
            original_remove(trainer, *args)
            return False

        def post_save(target, *args, **kwargs):
            """Exercise the actual model write before a labelled checkpoint fault."""
            original_save(target, *args, **kwargs)
            raise RuntimeError("remedy isolated owned-save refusal")

        for model, attribute, failure in ((Trainer, "remove_item", partial), (OwnedPokemon, "save", post_save)):
            before = self.state()
            with patch.object(model, attribute, failure):
                try:
                    self.command("use", item + "=3")
                except RuntimeError:
                    pass
            self.assertEqual(self.state(), before)

    def fusion_new(self, item):
        """A reservation alone is ineligible; the current Fusion receives the same effect."""
        from pokemon.services.placement import PlacementService

        self.prepare_new(item)
        self.player.trainer.add_item(item, 1)
        PlacementService(self.player.storage).reserve_for_fusion(self.mon)
        before = self.row()
        self.command("use", item + "=fusion")
        self.assertEqual(self.row(), before)
        self.player.db.fusion_id = str(self.mon.pk)
        self.command("use", item + "=fusion")
        self.outcome(item, before)
        self.assertEqual(self.player.trainer.get_item_quantity(item), 0)

    def contention_new(self, item):
        """Two independent final-copy requests commit exactly one useful effect."""
        from django.db import close_old_connections
        from pokemon.services.field_recovery_equivalents import FieldRecoveryEquivalentUse

        self.prepare_new(item)
        self.player.trainer.add_item(item, 1)
        before, barrier = self.row(), Barrier(2)

        def run(unused):
            """Isolate concurrent service requests from the captured menu transport."""
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    return bool(FieldRecoveryEquivalentUse(self.player).use(item, "3"))
                except ValueError:
                    return False
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as workers:
            self.assertEqual(sum(workers.map(run, range(2))), 1)
        self.outcome(item, before)
        self.assertEqual(self.player.trainer.get_item_quantity(item), 0)


for item in ITEMS:
    for mode in ("flow", "no_effect", "guards", "rollback", "fusion", "contention"):
        def test(self, item=item, mode=mode):
            """Run an independently counted exact-item field medicine route."""
            getattr(self, mode + "_new")(item)
        setattr(RemedyRecoveryCases, "test_new_" + item.lower().replace(" ", "") + "_" + mode, test)


if __name__ == "__main__":
    from ordinary_player_fixtures import OrdinaryPlayerFixtures
    from isolated_battle_logs import IsolatedBattleLogs

    try:
        with IsolatedPostgres() as database:
            database.create_model_tables()
            acquisition.load_runtime()
            with OrdinaryPlayerFixtures("four-field-remedies-935"), IsolatedBattleLogs():
                from commands.player import cmd_pokedex
                acquisition.COMMANDS["itemdex"] = (cmd_pokedex, cmd_pokedex.CmdItemdexSearch)
                names = [name for name in RemedyRecoveryCases.__dict__ if name.startswith("test_new_")]
                result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(RemedyRecoveryCases(name) for name in names))
    finally:
        if os.environ.get("PF2_REMEDY_EVIDENCE"):
            Path(os.environ["PF2_REMEDY_EVIDENCE"]).write_text(json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf8")
    raise SystemExit(not result.wasSuccessful())

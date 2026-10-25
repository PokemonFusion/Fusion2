"""Thirteen named PF2 flavor snacks through real menus, field commands and SQL."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
from threading import Barrier
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import item_availability_cases as core

BATCHES = {
    889: ("Bluk Berry", "Nanab Berry", "Pinap Berry", "Wepear Berry"),
    890: ("Cornn Berry", "Magost Berry", "Nomel Berry", "Rabuta Berry"),
    891: ("Belue Berry", "Durin Berry", "Pamtre Berry", "Spelon Berry", "Watmel Berry"),
}
EVIDENCE = []


class FlavorSnackCases(unittest.TestCase):
    """Separate stock/condition prerequisites from actual ordinary item use."""

    native = core.AcquisitionCases.native
    command = core.AcquisitionCases.command
    reply = core.AcquisitionCases.reply
    state = core.AcquisitionCases.state
    tearDown = core.AcquisitionCases.tearDown

    def setUp(self):
        """Author one finite fixture counter and otherwise reuse field identity setup."""
        core.AcquisitionCases.setUp(self)
        self.room.db.store_buy_only = True
        self.room.db.store_inventory = {
            item: {"price": 100, "quantity": 5}
            for item in ("Razz Berry", *[name for batch in BATCHES.values() for name in batch])
        }

    def buy(self, item, amount=1):
        """Use actual ordinary store replies; never grant a bag copy."""
        before = self.state()
        self.command("store")
        for text in ("1", f"{item} {amount}", "back", "q"):
            self.reply(text)
        self.assertEqual(self.player.trainer.get_item_quantity(item), amount)
        after = self.state()
        self.assertEqual(after["wallet"], before["wallet"] - 100 * amount)
        self.assertEqual(after["stock"][item]["quantity"], before["stock"][item]["quantity"] - amount)
        EVIDENCE.append({"case": self._testMethodName, "kind": "ordinary-purchase",
                         "commands": ["+store", "1", f"{item} {amount}", "back", "q"],
                         "before": before, "after": after})

    def record(self, text):
        """Capture the real parser, outcome messages and independent saved rows."""
        before, start = self.state(), len(self.player.messages)
        result = self.command("berry", text)
        EVIDENCE.append({"case": self._testMethodName, "command": "+berry " + text,
                         "before": before, "after": self.state(),
                         "messages": list(map(str, self.player.messages[start:]))})
        return result

    def purchased(self, item):
        """The selected purchased berry heals10, preserving held copy and non-HP state."""
        from django.db import connections

        self.buy("Razz Berry")
        self.buy(item, 2)
        self.command("hold", "3=" + item)
        self.assertEqual(self.player.trainer.get_item_quantity(item), 1)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=1, status="brn")
        before = self.state()
        self.command("use", item + "=3")
        self.assertEqual(self.state(), before)
        self.record("snack " + item.swapcase() + "=" + str(self.mon.pk))
        after = self.state()
        self.assertEqual(self.player.trainer.get_item_quantity(item), 0)
        self.assertEqual(self.player.trainer.get_item_quantity("Razz Berry"), 1)
        old = next(r for r in before["owned"] if r["pk"] == self.mon.pk)
        new = next(r for r in after["owned"] if r["pk"] == self.mon.pk)
        self.assertEqual(new["current_hp"], 11)
        self.assertEqual({k: v for k, v in old.items() if k != "current_hp"},
                         {k: v for k, v in new.items() if k != "current_hp"})
        self.assertEqual(new["held_item"], item)
        self.assertEqual(after["pp"], before["pp"])
        before = self.state()
        self.record("snack " + item + "=3")
        self.assertEqual(self.state(), before)  # Held-only copy is not a snack.
        connections.close_all()
        OwnedPokemon.flush_cached_instance(self.mon)
        self.assertEqual(OwnedPokemon.objects.get(pk=self.mon.pk).current_hp, 11)

    def guarded(self, item):
        """Actual full/fainted/egg/boxed/foreign/current-battle guards spend nothing."""
        from pokemon.services.berry_snack import BerrySnack

        self.buy(item)
        maximum = get_max_hp(self.mon)
        for updates in ({"current_hp": maximum}, {"current_hp": 0},
                        {"current_hp": 1, "is_egg": True}):
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(**updates)
            before = self.state()
            self.record("snack " + item + "=3")
            self.assertEqual(self.state(), before)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=1, is_egg=False)
        for marker in (True, 0, "stale-battle-id"):
            self.player.db.battle_lock = marker
            before = self.state()
            self.record("snack " + item + "=3")
            self.assertEqual(self.state(), before)
        self.player.db.battle_lock = False
        foreign = self.native("Mew", 3, self.players[1])
        before = self.state()
        self.record("snack " + item + "=" + str(foreign.pk))
        self.assertEqual(self.state(), before)
        PlacementService(self.player.storage).to_box(self.mon)
        before = self.state()
        self.record("snack " + item + "=" + str(self.mon.pk))
        self.assertEqual(self.state(), before)
        with self.assertRaises(ValueError):
            BerrySnack(self.player).use(item, str(self.mon.pk), move="1")
        self.assertEqual(self.state(), before)
        for text in ("snack Oran Berry=3", "snack Unknown Berry=3",
                     "snack " + item, "snack " + item + "=", "snack " + item + "=3/1"):
            self.record(text)
            self.assertEqual(self.state(), before)

    def fusion(self, item):
        """Only the actual current Fusion can receive a capped useful snack."""
        self.buy(item)
        maximum = get_max_hp(self.mon)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=maximum - 3)
        PlacementService(self.player.storage).reserve_for_fusion(self.mon)
        self.player.db.fusion_id = "stale-other-pokemon"
        before = self.state()
        self.record("snack " + item + "=fusion")
        self.assertEqual(self.state(), before)
        self.player.db.fusion_id = str(self.mon.pk)
        self.record("snack " + item + "=fusion")
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("current_hp", flat=True).get(), maximum)
        self.assertEqual(self.player.trainer.get_item_quantity(item), 0)

    def rollback(self, item):
        """Partial debit, saved HP failure and outer rollback restore data/notices."""
        from django.db import transaction

        self.buy(item)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=1)
        before = self.state()
        remove = Trainer.remove_item

        def partial(trainer, *args, **kwargs):
            remove(trainer, *args, **kwargs)
            return False

        with patch.object(Trainer, "remove_item", partial):
            self.record("snack " + item + "=3")
        self.assertEqual(self.state(), before)
        save = OwnedPokemon.save

        def fail(mon, *args, **kwargs):
            save(mon, *args, **kwargs)
            raise RuntimeError("flavor snack post-save prerequisite probe")

        with patch.object(OwnedPokemon, "save", fail):
            self.record("snack " + item + "=3")
        self.assertEqual(self.state(), before)
        start = len(self.player.messages)
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.record("snack " + item + "=3")
                raise RuntimeError("flavor snack outer rollback probe")
        self.assertEqual(self.state(), before)
        self.assertFalse(any("Used " + item in str(m) for m in self.player.messages[start:]))
        self.record("snack " + item + "=3")
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("current_hp", flat=True).get(), 11)

    def contention(self, item):
        """Two fresh field requests can spend only one final purchased copy."""
        from django.db import close_old_connections
        from pokemon.services.berry_snack import BerrySnack

        self.buy(item)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=1)
        barrier = Barrier(2)

        def worker(_):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    return BerrySnack(self.player).use(item, "3")
                except ValueError:
                    return False
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(worker, range(2)))
        self.assertEqual(results.count(True), 1)
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("current_hp", flat=True).get(), 11)
        self.assertEqual(self.player.trainer.get_item_quantity(item), 0)
        EVIDENCE.append({"case": self._testMethodName, "kind": "concurrent-final-copy",
                         "results": results, "after": self.state()})

    def battle_exclusion(self, item):
        """A held flavor copy never heals or opens a manual action through this route."""
        self.buy(item, 2)
        self.command("hold", "3=" + item)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=1)
        foe = create_battle_pokemon("Dugtrio", 50, is_wild=True, move_names=["Sand Attack"])
        self.session = BattleSession(self.player)
        self.session._track_temp_opponent_team([foe])
        self.session._select_opponent = lambda: (foe, "Wild Dugtrio", BattleType.WILD, "Labelled passive-opponent fixture")
        self.session.start()
        before = self.state()
        self.command("item", item + "=3")
        self.assertEqual(self.state(), before)
        self.assertFalse(any(self.session.state.declare.values()))
        self.command("attack", "Tackle B1")
        active = self.session.battle.participants[0].active[0]
        self.assertEqual(active.hp, 1)
        self.assertEqual(self.player.trainer.get_item_quantity(item), 1)
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("held_item", flat=True).get(), item)


def add_case(item, method):
    """Count exact named positive items and one shared-boundary case per batch."""
    def test(self):
        getattr(self, method)(item)
    key = "".join(c.lower() for c in item if c.isalnum())
    setattr(FlavorSnackCases, "test_" + method + "_" + key, test)


for names in BATCHES.values():
    for item in names:
        add_case(item, "purchased")
    for method in ("guarded", "fusion", "rollback", "contention", "battle_exclusion"):
        add_case(names[0], method)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        core.load_runtime()
        import evennia
        from evennia.commands.command import Command
        with patch.object(evennia, "Command", Command):
            from commands.player import cmd_berry, cmd_battle_item
        core.COMMANDS["berry"] = (cmd_berry, cmd_berry.CmdBerry)
        core.COMMANDS["item"] = (cmd_battle_item, cmd_battle_item.CmdBattleItem)
        from evennia.objects.models import ObjectDB
        from django.contrib.contenttypes.models import ContentType
        ContentType.objects.get_for_model(ObjectDB)
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.trainer import Trainer
        from pokemon.helpers.pokemon_helpers import get_max_hp
        from pokemon.services.placement import PlacementService
        from pokemon.battle.battleinstance import BattleSession, BattleType, create_battle_pokemon
        try:
            result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FlavorSnackCases))
        finally:
            if os.environ.get("PF2_FLAVOR_SNACK_EVIDENCE"):
                Path(os.environ["PF2_FLAVOR_SNACK_EVIDENCE"]).write_text(json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())


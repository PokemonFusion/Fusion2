"""Chesto, Sitrus and Lum through real growing commands and disposable SQL."""

from datetime import timedelta
import json
import os
from pathlib import Path
import unittest

from isolated_postgres import IsolatedPostgres
import nursery_seed_cases as prior
import berry_growing_cases as legacy
import item_availability_cases as acquisition


SEEDS = {"Chesto Berry": "slp", "Sitrus Berry": "", "Lum Berry": "tox"}
EVIDENCE = legacy.EVIDENCE


class NextSeedCases(prior.SeedGrowingCases):
    """Retain cycle/guard/fault coverage and verify each harvested useful effect."""

    def buy(self, item, amount=1):
        """Pay the actual source price; do not infer it from the previous batch."""
        before = self.state()
        price = before["stock"][item]["price"]
        self.command("store")
        for reply in ("1", f"{item} {amount}", "back", "q"):
            self.reply(reply)
        after = self.state()
        self.assertEqual(after["wallet"], before["wallet"] - price * amount)
        self.assertEqual(after["stock"][item]["quantity"], before["stock"][item]["quantity"] - amount)
        self.assertIn(item, self.command("inventory"))

    def consume_harvest(self):
        """Label injury/status setup separately; normal +use must have real utility."""
        from pokemon.helpers.pokemon_helpers import get_max_hp

        hp = get_max_hp(self.mon)
        prior.OwnedPokemon.objects.filter(pk=self.mon.pk).update(
            status=SEEDS[self.seed], current_hp=hp - int(self.seed == "Sitrus Berry"))
        EVIDENCE.append({"label": "separate-use-prerequisite", "seed": self.seed,
                         "status": SEEDS[self.seed], "hp_deficit": int(self.seed == "Sitrus Berry")})
        before = self.player.trainer.get_item_quantity(self.seed)
        self.command("use", self.seed + "=3")
        row = prior.OwnedPokemon.objects.values("status", "current_hp").get(pk=self.mon.pk)
        self.assertEqual(row, {"status": "", "current_hp": hp})
        self.assertEqual(self.player.trainer.get_item_quantity(self.seed), before - 1)
        resources = self.state()
        self.command("use", self.seed + "=3")
        self.assertEqual(self.state(), resources)

    def masks(self, mask):
        """All sixteen water patterns retain exact yield, identity and one harvest."""
        cycle, planted = self.plant(), self.now
        for stage in range(4):
            self.now = planted + timedelta(hours=stage)
            if mask & (1 << stage):
                self.record("water")
                before = self.state()
                self.record("water")
                self.assertEqual(self.state(), before)
        self.now = planted + timedelta(hours=4)
        self.assertEqual(self.growing().status()["berry"], self.seed)
        self.record("status")
        self.assertIn(self.seed, self.player.messages[-1])
        self.record("harvest")
        self.assertEqual(self.player.trainer.get_item_quantity(self.seed), 1 + mask.bit_count())
        self.assertEqual(self.state()["bed"]["last_harvest_cycle"], cycle)
        before = self.state()
        self.growing().operate("harvest", cycle=cycle)
        self.record("harvest")
        self.assertEqual(self.state(), before)
        self.consume_harvest()

    def counter(self):
        """New Chesto source and existing Sitrus/Lum offers never refill on retries."""
        from evennia.utils.create import create_object
        from pokemon.services.battle_rewards import BattleRewards
        from pokemon.services.item_counter import BerryNursery, ItemCounter
        from pokemon.services.finite_item_supply import HeldStapleSupply

        hub = create_object("typeclasses.rooms.FusionRoom", key="next-seed-hub", nohome=True)
        old = BerryNursery.install(hub)
        old_stock = BattleRewards.stored_attribute(old, "store_inventory")
        counter = ItemCounter("world/chesto_seed_counter.json")
        nursery = counter.install(hub)
        held = HeldStapleSupply.install(hub)
        self.installed_objects.append(hub.pk)
        for marker in ("counter_oran-razz-nursery-v1", "counter_chesto-berry-seed-counter-v1",
                       HeldStapleSupply.marker):
            receipt = BattleRewards.stored_attribute(hub, marker)
            self.installed_objects.extend(receipt[key] for key in ("room", "entrance", "return_exit"))
        self.room = hub
        self.player.location = hub
        self.player.character.location = hub
        self.travel("chestoseed" if self.seed == "Chesto Berry" else HeldStapleSupply.entrance)
        self.buy(self.seed)
        paid_stock = BattleRewards.stored_attribute(self.room, "store_inventory")
        self.assertEqual(counter.install(hub).pk, nursery.pk)
        self.assertEqual(HeldStapleSupply.install(hub).pk, held.pk)
        self.assertEqual(BattleRewards.stored_attribute(self.room, "store_inventory"), paid_stock)
        if self.room.pk != nursery.pk:
            self.travel("back")
            self.travel("chestoseed")
        self.record("plant " + self.seed)
        for _ in range(4):
            self.record("water")
            self.now += timedelta(hours=1)
        self.record("harvest")
        self.assertEqual(self.player.trainer.get_item_quantity(self.seed), 5)
        self.consume_harvest()
        self.assertEqual(BattleRewards.stored_attribute(old, "store_inventory"), old_stock)

    def travel(self, name):
        """Drive the real exit while adapting only the captured session transport."""
        from evennia.objects.models import ObjectDB

        entrance = ObjectDB.objects.get(db_location_id=self.room.pk, db_key=name)

        def move(destination, **kwargs):
            """Persist ordinary movement on this fixture's real character."""
            moved = self.player.character.move_to(destination, quiet=True, move_hooks=False)
            if moved:
                self.player.location = self.room = destination
            return moved

        self.player.move_to = move
        command = entrance.exit_command()
        command.caller, command.obj, command.args = self.player, entrance, ""
        command.func()
        self.assertEqual(ObjectDB.objects.values_list("db_location_id", flat=True).get(pk=self.player.pk),
                         entrance.db_destination_id)
        EVIDENCE.append({"label": "ordinary-travel", "exit": name, "destination": self.room.pk})


def cases():
    """Count all three exact names, sixteen masks and five failure/source routes."""
    suite = unittest.TestSuite()
    for seed in SEEDS:
        cls = type(seed.replace(" ", "") + "Cases", (NextSeedCases,), {"seed": seed})
        for mask in range(16):
            name = "test_water_mask_" + str(mask)
            setattr(cls, name, lambda self, mask=mask: self.masks(mask))
        for method in ("stale", "contention", "rollback", "current_guards", "counter"):
            setattr(cls, "test_" + method, lambda self, method=method: getattr(self, method)())
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
    return suite


if __name__ == "__main__":
    from ordinary_player_fixtures import OrdinaryPlayerFixtures

    try:
        with IsolatedPostgres() as database:
            database.create_model_tables()
            with OrdinaryPlayerFixtures("nursery-next-three"):
                acquisition.load_runtime()
                from commands.player import cmd_berry

                acquisition.COMMANDS["berry"] = (cmd_berry, cmd_berry.CmdBerry)
                from django.contrib.contenttypes.models import ContentType
                from evennia.objects.models import ObjectDB
                from pokemon.models.berries import BerryBed
                from pokemon.models.core import OwnedPokemon
                from pokemon.models.trainer import Trainer
                from pokemon.services.berry_growing import BerryGrowing, BerryGrowingError

                ContentType.objects.get_for_model(ObjectDB)
                # Rebind only this standalone process's reused fixture dependencies.
                prior.SEEDS = SEEDS
                prior.Trainer, prior.OwnedPokemon = Trainer, OwnedPokemon
                prior.BerryGrowingError = BerryGrowingError
                for name, value in {"ObjectDB": ObjectDB, "BerryBed": BerryBed,
                                    "OwnedPokemon": OwnedPokemon, "Trainer": Trainer,
                                    "BerryGrowing": BerryGrowing, "BerryGrowingError": BerryGrowingError}.items():
                    setattr(legacy, name, value)
                    setattr(prior, name, value)
                result = unittest.TextTestRunner(verbosity=2).run(cases())
    finally:
        if os.environ.get("PF2_NURSERY_NEXT_EVIDENCE"):
            Path(os.environ["PF2_NURSERY_NEXT_EVIDENCE"]).write_text(
                json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
    raise SystemExit(not result.wasSuccessful())

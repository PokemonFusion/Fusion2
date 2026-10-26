"""Optional finite counter travel/purchase/battle flows in a disposable SQL world."""

import json
import os
from pathlib import Path
import unittest
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
import item_availability_cases as acquisition
import battle_booster_cases as boosters
import battle_item_validation_cases as fixtures


class BoosterPlayer(fixtures.ItemPlayer, acquisition.AcquisitionPlayer):
    """Delegate real player stock/currency APIs while capturing client transport."""


class BoosterSourceCases(unittest.TestCase):
    """Each actual optional offer reaches its named paid battle effect and restore."""

    command = fixtures.ItemSessionFixture.command
    state = fixtures.ItemSessionFixture.state
    snapshot = fixtures.ItemSessionFixture.snapshot
    start = fixtures.ItemSessionFixture.start
    rebuild = fixtures.ItemSessionFixture.rebuild
    find = fixtures.ItemSessionFixture.find
    action_state = staticmethod(fixtures.ItemSessionFixture.action_state)
    actor = boosters.BattleBoosterCases.actor
    flow = boosters.BattleBoosterCases.flow
    record = boosters.BattleBoosterCases.record
    assert_effect = boosters.BattleBoosterCases.assert_effect
    fixture_level = 20

    def setUp(self):
        """Author a tagged finite counter and wallet; initial bags remain empty."""
        from evennia.utils.create import create_object
        from pokemon.services.item_counter import ItemCounter

        fixtures.ItemSessionFixture.setUp(self)
        self.counter = ItemCounter("world/battle_booster_counter.json")
        self.hub = create_object(
            "typeclasses.rooms.FusionRoom", key="booster-source-hub-" + uuid4().hex, nohome=True
        )
        self.room = self.counter.install(self.hub)
        for index, old in enumerate(self.players):
            player = BoosterPlayer(old.character, old.trainer, old.storage)
            player.pk, player.location = player.character.pk, self.hub
            fixtures.ObjectDB.objects.filter(pk=player.pk).update(db_location_id=self.hub.pk)
            self.players[index] = player
            player.move_to = lambda destination, *args, _player=player, **kwargs: self.move(
                _player, destination
            )
        self.player = self.players[0]
        self.player.trainer.money = 1000000
        self.player.trainer.save(update_fields=["money"])

    def tearDown(self):
        """Release only this source's menus/battles and tagged recipe objects."""
        from pokemon.services.battle_rewards import BattleRewards

        for player in self.players:
            if player.ndb._evmenu:
                player.ndb._evmenu.close_menu()
        fixtures.ItemSessionFixture.tearDown(self)
        marker = "counter_" + self.counter.recipe()["key"]
        receipt = BattleRewards.stored_attribute(self.hub, marker)
        if receipt:
            fixtures.ObjectDB.objects.filter(
                pk__in=[receipt["room"], receipt["entrance"], receipt["return_exit"]]
            ).delete()
            self.hub.attributes.remove(marker)

    def move(self, player, destination):
        """Use the actual character movement while adapting transport location."""
        moved = player.character.move_to(destination, quiet=True, move_hooks=False)
        if moved:
            player.location = destination
        return moved

    def travel(self, key):
        """Execute the reviewed authored Exit command and its normal lock."""
        exit_object = fixtures.ObjectDB.objects.get(
            db_location_id=self.player.location.pk, db_key=key
        )
        command = exit_object.exit_command()
        command.caller, command.obj, command.args = self.player, exit_object, ""
        command.func()
        self.assertEqual(
            fixtures.ObjectDB.objects.filter(pk=self.player.pk)
            .values_list("db_location_id", flat=True)
            .get(),
            exit_object.db_destination_id,
        )

    def give(self, item, quantity=1):
        """Replace the setup-grant hook with an actual ordinary finite-stock purchase."""
        self.assertEqual(quantity, 1)
        self.travel("boosters")
        self.room.attributes.reset_cache()
        before = dict(self.room.db.store_inventory)
        wallet = self.player.trainer.money
        acquisition.AcquisitionCases.command(self, "store")
        for text in ("1", item + " 1", "back", "q"):
            acquisition.AcquisitionCases.reply(self, text)
        self.room.attributes.reset_cache()
        after = dict(self.room.db.store_inventory)
        self.assertEqual(self.player.trainer.get_item_quantity(item), 1)
        self.player.trainer.refresh_from_db()
        self.assertEqual(self.player.trainer.money, wallet - before[item]["price"])
        self.assertEqual(after[item]["quantity"], before[item]["quantity"] - 1)
        self.assertIn(item, acquisition.AcquisitionCases.command(self, "inventory"))
        count = fixtures.ObjectDB.objects.count()
        self.assertEqual(self.counter.install(self.hub).pk, self.room.pk)
        self.assertEqual(fixtures.ObjectDB.objects.count(), count)
        self.room.attributes.reset_cache()
        self.assertEqual(dict(self.room.db.store_inventory), after)
        boosters.EVIDENCE.append(
            {
                "case": self.id(),
                "kind": "optional finite counter purchase",
                "commands": ["boosters", "+store", "1", item + " 1", "back", "q", "+inventory"],
                "item": item,
                "wallet_before": wallet,
                "wallet_after": self.player.trainer.money,
                "stock_before": before,
                "stock_after": after,
                "world_installed": False,
            }
        )


for item in [*boosters.ITEMS, *boosters.CONDITIONS]:

    def source_case(self, selected=item):
        """Travel, buy, inspect, +item, restore twice, end and return to the source hub."""
        self.flow(selected)
        self.session.end()
        self.session = None
        self.travel("back")

    setattr(
        BoosterSourceCases, "test_source_" + item.replace(" ", "").replace(".", ""), source_case
    )


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        fixtures.load_runtime()
        acquisition.load_runtime()
        from django.contrib.contenttypes.models import ContentType

        ContentType.objects.get_or_create(app_label="objects", model="objectdb")
        try:
            result = unittest.TextTestRunner(verbosity=2).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(BoosterSourceCases)
            )
        finally:
            if os.environ.get("PF2_BOOSTER_EVIDENCE"):
                Path(os.environ["PF2_BOOSTER_EVIDENCE"]).write_text(
                    json.dumps(boosters.EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8"
                )
        raise SystemExit(not result.wasSuccessful())

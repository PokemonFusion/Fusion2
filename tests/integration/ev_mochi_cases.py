"""Seven mochi through real +store/+use, fresh SQL and shared field controls."""

import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
import field_training_cases as legacy
import item_availability_cases as acquisition

MOCHI = {
    "Health Mochi": (0, 10),
    "Muscle Mochi": (1, 10),
    "Resist Mochi": (2, 10),
    "Genius Mochi": (3, 10),
    "Clever Mochi": (4, 10),
    "Swift Mochi": (5, 10),
}
EVIDENCE = legacy.EVIDENCE


class MochiPlayer(legacy.TrainingPlayer, acquisition.AcquisitionPlayer):
    """Capture menus/transport while delegating all actual player operations."""


class MochiCases(legacy.FieldTrainingCases):
    """Extend shared vitamin/feather cases, plus the reset's independent controls."""

    def setUp(self):
        """Create real tagged owner/party/stock, preserving all legacy training setup."""
        super().setUp()
        self.player = MochiPlayer(self.character, self.trainer, self.storage)
        self.player.pk = self.character.pk
        self.players, self.session = [self.player], None
        self.room = ObjectDB.objects.create(db_key="mochi-shop-" + uuid4().hex)
        self.player.location = self.room
        self.room.db.is_item_shop, self.room.db.store_buy_only = True, True
        self.room.db.store_inventory = {name: {"price": 10000, "quantity": 2} for name in MOCHI}
        stock = dict(self.room.db.store_inventory)
        stock["Fresh-Start Mochi"] = {"price": 20000, "quantity": 1}
        self.room.db.store_inventory = stock
        self.trainer.money = 1000000
        self.trainer.save(update_fields=["money"])

    def tearDown(self):
        """Close only this fixture's menu/session before disposable-schema removal."""
        if self.session:
            self.session.end()
        super().tearDown()

    def buy(self, item):
        """Acquire an authored-priced copy through production +store and real menu input."""
        before = self.trainer.get_item_quantity(item)
        wallet = Trainer.objects.filter(pk=self.trainer.pk).values_list("money", flat=True).get()
        self.command("", "store")
        for text in ("1", item + " 1", "back", "q"):
            command = CmdEvMenuNode()
            command.caller, command.raw_string, command.session = self.player, text, None
            command.func()
        self.assertEqual(self.trainer.get_item_quantity(item), before + 1)
        price = 20000 if item == "Fresh-Start Mochi" else 10000
        self.assertEqual(
            Trainer.objects.filter(pk=self.trainer.pk).values_list("money", flat=True).get(),
            wallet - price,
        )
        self.assertIn(item, self.command("", "inventory"))
        selector = "fusion" if str(self.character.db.fusion_id or "") == str(self.mon.pk) else "3"
        self.assertIn(str(self.mon.pk), self.command(selector, "party"))

    def purchased_flow(self, item):
        """A paid copy trains through +use, reloads and reaches a real battle builder."""
        self.prepare(item)
        self.buy(item)
        before, stats = self.snapshot(), get_stats(self.fresh())
        self.record("purchased-mochi-use", item + "=3")
        after = self.snapshot()
        index, amount = MOCHI[item]
        expected = list(before["pokemon"]["evs"])
        expected[index] += amount
        self.assertEqual(after["pokemon"]["evs"], expected)
        self.assertEqual(self.trainer.get_item_quantity(item), 0)
        current = get_stats(self.fresh())
        self.assertGreater(current[legacy.STATS[index]], stats[legacy.STATS[index]])
        self.assertEqual(after["pokemon"]["current_hp"], current["hp"] - 17)
        self.assert_preserved(before, after)
        self.assert_battle_stats(current)

    def assert_preserved(self, before, after):
        """Training changes only EVs/HP and its one bag debit."""
        for key, value in before["pokemon"].items():
            if key not in {"evs", "current_hp"}:
                self.assertEqual(after["pokemon"][key], value, key)
        for key in ("placement", "learned", "active", "sets", "boosts"):
            self.assertEqual(after[key], before[key], key)

    def assert_battle_stats(self, expected):
        """Use a production session and ordinary attack after the saved training change."""
        with patch(
            "pokemon.battle.battleinstance.search_object",
            lambda query: [self.player] if str(query).lstrip("#") == str(self.player.pk) else [],
        ):
            self.session = acquisition.BattleSession(self.player)
            foe = acquisition.create_battle_pokemon(
                "Magikarp", 100, is_wild=True, move_names=["Splash"]
            )
            self.session._track_temp_opponent_team([foe])
            self.session._select_opponent = lambda: (
                foe,
                "Fixture Magikarp",
                acquisition.BattleType.WILD,
                "Mochi stats",
            )
            self.session.start()
            holder = self.session.battle.participants[0].active[0]
            actual = holder.base_stats
            self.assertEqual({key: getattr(actual, key) for key in expected}, expected)
            turn = self.session.battle.turn_count
            acquisition.AcquisitionCases.command(self, "attack", "Water Gun")
            self.assertEqual(self.session.battle.turn_count, turn + 1)
            self.assertFalse(getattr(self.session.battle, "_callback_failures", []))
            self.session.end()
            self.session = None

    def reset_prepare(self, *, evs=None, hp=None):
        """Set labelled useful EVs and preserve a real calculated HP deficit."""
        self.state(
            evs=evs if evs is not None else [100, 100, 100, 100, 100, 10],
            status="psn",
            friendship=203,
            held_item="Leftovers",
            flags=["ordinary-field-training"],
        )
        maximum = get_max_hp(self.fresh())
        self.state(current_hp=maximum - 17 if hp is None else hp)

    def test_purchased_reset_clears_all_six_and_preserves_later_battle_stats(self):
        """One real reset copy clears the whole vector and keeps the absolute deficit."""
        self.reset_prepare()
        self.buy("Fresh-Start Mochi")
        before = self.snapshot()
        self.record("purchased-reset-use", "Fresh-Start Mochi=3")
        after = self.snapshot()
        self.assertEqual(after["pokemon"]["evs"], [0] * 6)
        self.assertEqual(self.trainer.get_item_quantity("Fresh-Start Mochi"), 0)
        stats = get_stats(self.fresh())
        self.assertEqual(after["pokemon"]["current_hp"], stats["hp"] - 17)
        self.assert_preserved(before, after)
        self.assert_battle_stats(stats)

    def test_reset_zero_no_effect_and_fainted_or_one_hp_remain_safe(self):
        """Reset never revives, kills a conscious holder or spends a no-effect copy."""
        self.give("Fresh-Start Mochi", 3)
        self.reset_prepare(evs=[0] * 6)
        before = self.snapshot()
        self.command("Fresh-Start Mochi=3")
        self.assertEqual(self.snapshot(), before)
        for hp in (0, 1):
            self.reset_prepare(evs=[252, 0, 0, 0, 0, 0], hp=hp)
            self.command("Fresh-Start Mochi=3")
            self.assertEqual(self.snapshot()["pokemon"]["current_hp"], hp)
            self.assertEqual(self.snapshot()["pokemon"]["evs"], [0] * 6)

    def test_reset_invalid_target_egg_box_and_selector_guards(self):
        """A reset reuses the same current owned field checks as the supplements."""
        self.reset_prepare()
        self.give("Fresh-Start Mochi")
        before = self.snapshot()
        for target in ("99", "party", "3/Atk", "Missing"):
            self.command("Fresh-Start Mochi=" + target)
            self.assertEqual(self.snapshot(), before)
        self.state(is_egg=True)
        before = self.snapshot()
        self.command("Fresh-Start Mochi=3")
        self.assertEqual(self.snapshot(), before)
        self.state(is_egg=False)
        PlacementService(self.storage).to_box(self.mon)
        before = self.snapshot()
        self.command("Fresh-Start Mochi=" + str(self.mon.pk))
        self.assertEqual(self.snapshot(), before)
        PlacementService(self.storage).to_party(self.mon, slot=3)
        PlacementService(self.storage).reserve_for_fusion(self.mon)
        before = self.snapshot()
        self.command("Fresh-Start Mochi=fusion")
        self.assertEqual(self.snapshot(), before)

    def test_reset_preserves_actual_hyper_training_and_current_fusion(self):
        """A real Gold Cap overlay survives a reset on the trainer's current Fusion."""
        self.reset_prepare()
        self.give("Gold Bottle Cap")  # labelled prerequisite, separate from mochi acquisition
        self.command("Gold Bottle Cap=3")
        self.assertTrue(
            all(
                "hypertrained:" + name in self.snapshot()["pokemon"]["flags"]
                for name in legacy.STATS
            )
        )
        PlacementService(self.storage).reserve_for_fusion(self.mon)
        self.character.db.fusion_id = str(self.mon.pk)
        self.buy("Fresh-Start Mochi")
        before = self.snapshot()
        self.command("Fresh-Start Mochi=fusion")
        after = self.snapshot()
        self.assertEqual(after["pokemon"]["evs"], [0] * 6)
        self.assertEqual(after["pokemon"]["ivs"], before["pokemon"]["ivs"])
        self.assertEqual(after["pokemon"]["flags"], before["pokemon"]["flags"])
        self.assertEqual(after["pokemon"]["current_hp"], get_max_hp(self.fresh()) - 17)
        self.assert_preserved(before, after)
        self.assertEqual(self.trainer.get_item_quantity("Fresh-Start Mochi"), 0)

    def test_reset_bad_saved_vectors_refuse_without_repair(self):
        """Malformed arrays are not silently cleared into a valid trained creature."""
        self.give("Fresh-Start Mochi")
        for evs in ([0] * 5, [-1, 0, 0, 0, 0, 0], [253, 0, 0, 0, 0, 0], [252, 252, 7, 0, 0, 0]):
            self.state(evs=evs)
            before = self.snapshot()
            self.command("Fresh-Start Mochi=3")
            self.assertEqual(self.snapshot(), before)

    def test_reset_fault_after_save_and_partial_debit_roll_back(self):
        """Real partial writes cannot leave a partly reset vector or lost copy."""
        self.reset_prepare()
        self.give("Fresh-Start Mochi")
        before = self.snapshot()
        original = OwnedPokemon.save

        def fault(pokemon, *args, **kwargs):
            """Fail after the real whole-vector/HP SQL save."""
            original(pokemon, *args, **kwargs)
            raise RuntimeError("post-reset fixture")

        with patch.object(OwnedPokemon, "save", fault):
            with self.assertRaisesRegex(RuntimeError, "post-reset"):
                self.command("Fresh-Start Mochi=3")
        self.assertEqual(self.snapshot(), before)
        original_debit = Trainer.remove_item

        def partial(trainer, *args):
            """Run production debit before reporting failure."""
            original_debit(trainer, *args)
            return False

        with patch.object(Trainer, "remove_item", partial):
            self.command("Fresh-Start Mochi=3")
        self.assertEqual(self.snapshot(), before)

    def test_outer_rollback_keeps_shared_references_and_success_unpublished(self):
        """Every new item restores SQL/cache and emits no premature success."""
        from django.db import transaction

        for item in (*MOCHI, "Fresh-Start Mochi"):
            self.reset_prepare() if item == "Fresh-Start Mochi" else self.prepare(item)
            self.give(item)
            before, stats = self.snapshot(), get_stats(self.fresh())
            offset = len(self.player.messages)
            with self.assertRaisesRegex(RuntimeError, "outer mochi fixture"):
                with transaction.atomic():
                    self.command(item + "=3")
                    self.assertFalse(
                        any(
                            str(message).startswith("Used ")
                            for message in self.player.messages[offset:]
                        )
                    )
                    self.assertEqual(self.mon.evs, before["pokemon"]["evs"])
                    raise RuntimeError("outer mochi fixture")
            self.assertEqual(self.snapshot(), before)
            self.assertEqual(get_stats(self.mon), stats)
            self.command(item + "=3")
            self.assertEqual(self.trainer.get_item_quantity(item), 0)

    def test_reset_and_different_stat_contention_preserve_committed_order(self):
        """One reset copy resets once; independent supplements retain useful updates."""
        self.reset_prepare()
        self.give("Fresh-Start Mochi")
        self.race(
            lambda: self.command("Fresh-Start Mochi=3"), lambda: self.command("Fresh-Start Mochi=3")
        )
        self.assertEqual(self.snapshot()["pokemon"]["evs"], [0] * 6)
        self.assertEqual(self.trainer.get_item_quantity("Fresh-Start Mochi"), 0)
        for item in ("Muscle Mochi", "Resist Mochi"):
            self.give(item)
        self.race(lambda: self.command("Muscle Mochi=3"), lambda: self.command("Resist Mochi=3"))
        self.assertEqual(self.snapshot()["pokemon"]["evs"], [0, 10, 10, 0, 0, 0])

    def test_authored_optional_counter_exit_purchase_use_and_retry(self):
        """The actual seven-offer recipe preserves finite stock after each paid use."""
        from evennia.utils.create import create_object
        from pokemon.services.battle_rewards import BattleRewards
        from pokemon.services.item_counter import ItemCounter

        hub = create_object(
            "typeclasses.rooms.FusionRoom", key="mochi-source-hub-" + uuid4().hex, nohome=True
        )
        counter = ItemCounter("world/ev_mochi_counter.json")
        room = counter.install(hub)
        marker = "counter_ev-mochi-counter-v1"
        receipt = BattleRewards.stored_attribute(hub, marker)
        identifiers = [hub.pk, receipt["room"], receipt["entrance"], receipt["return_exit"]]
        self.addCleanup(lambda: ObjectDB.objects.filter(pk__in=identifiers).delete())
        self.player.location = hub
        self.character.location = hub

        def move(destination, **kwargs):
            """Use production movement while adapting only client transport."""
            moved = self.character.move_to(destination, quiet=True, move_hooks=False)
            if moved:
                self.player.location = destination
            return moved

        self.player.move_to = move
        entrance = ObjectDB.objects.get(db_location=hub, db_key="mochi")
        command = entrance.exit_command()
        command.caller, command.obj, command.args = self.player, entrance, ""
        command.func()
        self.assertEqual(
            ObjectDB.objects.filter(pk=self.player.pk)
            .values_list("db_location_id", flat=True)
            .get(),
            room.pk,
        )
        self.room = room
        for item in (*MOCHI, "Fresh-Start Mochi"):
            self.buy(item)
            self.command(item + "=3")
            self.assertEqual(self.trainer.get_item_quantity(item), 0)
        self.assertEqual(self.snapshot()["pokemon"]["evs"], [0] * 6)
        stock = BattleRewards.stored_attribute(room, "store_inventory")
        self.assertEqual(counter.install(hub).pk, room.pk)
        self.assertEqual(BattleRewards.stored_attribute(room, "store_inventory"), stock)
        self.assertIsNone(BattleRewards.stored_attribute(room, "item_replenishment"))
        self.assertEqual(stock["Fresh-Start Mochi"]["quantity"], 0)
        self.assertTrue(all(stock[item]["quantity"] == 1 for item in MOCHI))


def add_flow(item):
    """Count each new paid supplement through its real source/use/battle route."""

    def test(self):
        """Acquire, train, reload and battle with the named supplement."""
        self.purchased_flow(item)

    setattr(MochiCases, "test_purchased_" + item.split()[0], test)


for item in MOCHI:
    add_flow(item)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        acquisition.load_runtime()
        import evennia
        from evennia.commands.command import Command
        from evennia.commands.cmdset import CmdSet

        with patch.object(evennia, "Command", Command), patch.object(evennia, "CmdSet", CmdSet):
            from evennia.utils.evmenu import CmdEvMenuNode
            from commands.player.cmd_inventory import CmdInventory, CmdUseItem
            from commands.player.cmd_party import CmdDepositPokemon, CmdSetHoldItem
            from commands.player.cmd_sheet import CmdSheetPokemon
            from commands.player.cmd_store import CmdStore
        from evennia.objects.models import ObjectDB
        from django.contrib.contenttypes.models import ContentType

        ContentType.objects.get_for_model(ObjectDB)
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon, get_max_hp, get_stats
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import (
            ActiveMoveslot,
            MovePPBoost,
            MovesetSlot,
            PokemonLearnedMove,
        )
        from pokemon.models.storage import PokemonPlacement, StorageBox, UserStorage
        from pokemon.models.trainer import Trainer, InventoryEntry
        from pokemon.services.field_items import FieldMedicineUse
        from pokemon.services.field_training import FieldTrainingUse
        from pokemon.services.placement import PlacementService
        from pokemon.user import User

        for name in (
            "ObjectDB",
            "create_owned_pokemon",
            "get_max_hp",
            "get_stats",
            "OwnedPokemon",
            "ActiveMoveslot",
            "MovePPBoost",
            "MovesetSlot",
            "PokemonLearnedMove",
            "PokemonPlacement",
            "StorageBox",
            "UserStorage",
            "Trainer",
            "InventoryEntry",
            "FieldMedicineUse",
            "FieldTrainingUse",
            "PlacementService",
            "User",
        ):
            setattr(legacy, name, globals()[name])
        legacy.COMMANDS = {
            "use": CmdUseItem,
            "inventory": CmdInventory,
            "party": CmdSheetPokemon,
            "deposit": CmdDepositPokemon,
            "hold": CmdSetHoldItem,
            "store": CmdStore,
        }
        legacy.TRAINING.update(MOCHI)
        try:
            result = unittest.TextTestRunner(verbosity=2).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(MochiCases)
            )
        finally:
            if os.environ.get("PF2_MOCHI_EVIDENCE"):
                Path(os.environ["PF2_MOCHI_EVIDENCE"]).write_text(
                    json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8"
                )
        raise SystemExit(not result.wasSuccessful())

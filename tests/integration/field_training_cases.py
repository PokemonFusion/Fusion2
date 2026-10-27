"""Prove ordinary EV training commands with real disposable PostgreSQL rows."""

import json
import os
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


class TrainingPlayer(PlayerView):
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


class FieldTrainingCases(unittest.TestCase):
    """Check all twelve field routes, canonical targets, persistence and atomic use."""

    def setUp(self):
        """Create a tagged ordinary owner with a genuinely gapped party."""
        self.character = ObjectDB.objects.create(db_key="field-training-768-" + uuid4().hex, db_typeclass_path="pokemon.user.User")
        self.trainer, _ = Trainer.objects.get_or_create(user=self.character, defaults={"trainer_number": Trainer.objects.count() + 1})
        self.storage, _ = UserStorage.objects.get_or_create(user=self.character)
        StorageBox.objects.create(storage=self.storage, name="Training Box")
        self.player = TrainingPlayer(self.character, self.trainer, self.storage)
        self.player.pk = self.character.pk
        self.mon = self.create_mon()
        self.mon.activemoveslot_set.filter(slot=2).update(slot=4)

    def tearDown(self):
        """Release any real menu on this disposable transport."""
        menu = self.player.ndb._evmenu
        if menu:
            menu.close_menu()

    def create_mon(self, slot=3, species="Mew", level=100):
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

    def fresh(self):
        """Recalculate expectations from independently fetched saved values."""
        FieldMedicineUse._refresh(self.mon, self.snapshot()["pokemon"])
        return self.mon

    def prepare(self, item, *, evs=None, hp=None):
        """Seed useful EVs and unrelated state separately from player input."""
        index, _ = TRAINING[item]
        if evs is None:
            evs = [0] * 6
            evs[index] = 3
        self.state(evs=evs, current_hp=1, status="psn", friendship=203,
                   held_item="Leftovers", flags=["ordinary-field-training"])
        maximum = get_max_hp(self.fresh())
        self.state(current_hp=maximum - 17 if hp is None else hp)

    def field_flow(self, item):
        """Discover, train and reload each real item through normal commands."""
        from django.db import connections

        self.prepare(item)
        self.give(item)
        self.assertIn(item, self.command("", "inventory"))
        self.assertIn(str(self.mon.pk), self.command("3", "party"))
        before = self.snapshot()
        stats_before = get_stats(self.fresh())
        self.mon._cached_stats = {name: 9999 for name in stats_before}
        self.record("ordinary-training-use-" + item, item + "=3")
        self.assertTrue(self.player.messages[-1].startswith("Used "), self.player.messages[-1])
        after = self.snapshot()
        index, amount = TRAINING[item]
        expected = before["pokemon"]["evs"].copy()
        expected[index] += amount
        self.assertEqual(after["pokemon"]["evs"], expected)
        self.assertEqual(self.trainer.get_item_quantity(item), 0)
        stats_after = get_stats(self.mon)
        self.assertGreater(stats_after[STATS[index]], stats_before[STATS[index]])
        self.assertEqual(after["pokemon"]["current_hp"], stats_after["hp"] - 17)
        for name, value in before["pokemon"].items():
            if name not in {"evs", "current_hp"}:
                self.assertEqual(after["pokemon"][name], value, name)
        for name in ("placement", "learned", "active", "sets", "boosts"):
            self.assertEqual(after[name], before[name], name)
        connections.close_all()
        OwnedPokemon.flush_cached_instance(self.mon)
        self.assertEqual(self.snapshot(), after)
        self.assertEqual(get_stats(self.fresh()), stats_after)

    def test_stat_and_total_partial_caps_for_every_item(self):
        """Both families can use the last point; vitamins do not stop at 100."""
        for item, (index, amount) in TRAINING.items():
            with self.subTest(item=item):
                self.give(item, 5)
                evs = [0] * 6
                evs[index] = 240
                self.prepare(item, evs=evs)
                self.command(item + "=3")
                self.assertEqual(self.snapshot()["pokemon"]["evs"][index], 240 + amount)
                evs[index] = 251
                self.prepare(item, evs=evs)
                self.record("stat-partial-cap", item + "=3")
                self.assertEqual(self.snapshot()["pokemon"]["evs"][index], 252)
                before = self.snapshot()
                self.command(item + "=3")
                self.assertEqual(self.snapshot(), before)
                evs = [0] * 6
                evs[(index + 1) % 6], evs[(index + 2) % 6], evs[(index + 3) % 6] = 252, 252, 5
                self.prepare(item, evs=evs)
                self.record("total-partial-cap", item + "=3")
                expected = evs.copy()
                expected[index] = 1
                self.assertEqual(self.snapshot()["pokemon"]["evs"], expected)
                self.assertEqual(sum(expected), 510)
                self.assertEqual(self.trainer.get_item_quantity(item), 2)
                before = self.snapshot()
                self.command(item + "=3")
                self.assertEqual(self.snapshot(), before)

    def test_vitamins_clip_to_two_stat_or_total_points(self):
        """A partial vitamin buys exactly the remaining capacity."""
        for item, (index, amount) in TRAINING.items():
            if amount != 10:
                continue
            self.give(item, 2)
            evs = [0] * 6
            evs[index] = 250
            self.prepare(item, evs=evs)
            self.command(item + "=3")
            self.assertEqual(self.snapshot()["pokemon"]["evs"][index], 252)
            evs = [0] * 6
            evs[(index + 1) % 6], evs[(index + 2) % 6], evs[(index + 3) % 6] = 252, 252, 4
            self.prepare(item, evs=evs)
            self.command(item + "=3")
            expected = evs.copy()
            expected[index] = 2
            self.assertEqual(self.snapshot()["pokemon"]["evs"], expected)
            self.assertEqual(self.trainer.get_item_quantity(item), 0)

    def test_ev_gain_is_useful_even_without_displayed_stat_change(self):
        """EVs persist immediately; rounding is not an excuse for a free item."""
        self.prepare("Muscle Feather", evs=[0] * 6)
        before_stats = get_stats(self.fresh())
        self.give("Muscle Feather")
        self.record("sub-stat-rounding", "Muscle Feather=3")
        self.assertEqual(self.snapshot()["pokemon"]["evs"], [0, 1, 0, 0, 0, 0])
        self.assertEqual(get_stats(self.mon), before_stats)
        self.assertEqual(self.trainer.get_item_quantity("Muscle Feather"), 0)

    def test_all_items_keep_fainted_targets_fainted(self):
        """Training can increase legal EVs at zero HP without reviving."""
        for item, (index, amount) in TRAINING.items():
            self.prepare(item, evs=[0] * 6, hp=0)
            self.give(item)
            self.record("fainted-training", item + "=3")
            row = self.snapshot()["pokemon"]
            self.assertEqual((row["current_hp"], row["evs"][index]), (0, amount))
            self.assertEqual(row["status"], "psn")
            self.assertEqual(self.trainer.get_item_quantity(item), 0)

    def test_hp_deficit_full_health_and_non_hp_training(self):
        """Match the field-berry convention for HP changes and injuries."""
        for item in TRAINING:
            for deficit in (0, 1, 23):
                self.prepare(item)
                old_max = get_max_hp(self.fresh())
                self.state(current_hp=old_max - deficit)
                self.give(item)
                self.command(item + "=3")
                self.assertEqual(self.snapshot()["pokemon"]["current_hp"], get_max_hp(self.mon) - deficit)

    def test_invalid_ev_arrays_are_rejected_without_normalization_or_debit(self):
        """Use real SQL-invalid-for-gameplay values that the column can store."""
        for evs in ([], [0] * 5, [0] * 7, [253, 0, 0, 0, 0, 0], [252, 252, 7, 0, 0, 0]):
            for item in TRAINING:
                self.give(item)
                self.state(evs=evs)
                before = self.snapshot()
                self.record("invalid-saved-evs", item + "=3")
                self.assertEqual(self.snapshot(), before)
                self.assertIn("Invalid saved EVs", self.player.messages[-1])

    def test_missing_stock_and_exact_normalized_inventory_aliases(self):
        """Require actual stock, but support full names and legacy row spellings."""
        for item, (index, amount) in TRAINING.items():
            self.prepare(item, evs=[0] * 6)
            before = self.snapshot()
            self.command(item + "=3")
            self.assertEqual(self.snapshot(), before)
            InventoryEntry.objects.create(owner=self.trainer, item_name=item.upper(), quantity=1)
            self.record("normalized-bag-alias", item.upper().replace(" ", "-") + "=" + str(self.mon.pk))
            self.assertEqual(self.snapshot()["pokemon"]["evs"][index], amount)
            self.assertEqual(self.trainer.get_item_quantity(item), 0)

    def test_current_fusion_aliases_and_normal_name_id_target_first(self):
        """All twelve can train the actual current Fusion, preserving gaps."""
        PlacementService(self.storage).reserve_for_fusion(self.mon)
        self.character.db.fusion_id = str(self.mon.pk)
        for number, item in enumerate(TRAINING):
            self.prepare(item, evs=[0] * 6)
            self.give(item)
            self.record("current-fusion-training", item + "=" + ("fusion", "self", "me")[number % 3])
            index, amount = TRAINING[item]
            self.assertEqual(self.snapshot()["pokemon"]["evs"][index], amount)
            self.assertEqual(self.trainer.get_item_quantity(item), 0)
        PlacementService(self.storage).return_from_fusion(self.mon, preferred_slot=3)
        self.character.db.fusion_id = None
        for args in ("Protein=Mew", "3=Protein", "Protein=" + str(self.mon.pk)):
            self.prepare("Protein", evs=[0] * 6)
            self.give("Protein")
            self.command(args)
            self.assertEqual(self.snapshot()["pokemon"]["evs"], [0, 10, 0, 0, 0, 0])

    def test_every_item_rejects_eggs_boxed_and_inactive_fusion(self):
        """Reuse the same canonical target guards rather than trusting old IDs."""
        for item in TRAINING:
            self.prepare(item)
            self.give(item)
            self.state(is_egg=True)
            before = self.snapshot()
            self.command(item + "=3")
            self.assertEqual(self.snapshot(), before)
            self.state(is_egg=False)
            self.assertIn("deposited", self.command(str(self.mon.pk), "deposit"))
            before = self.snapshot()
            self.record("post-deposit-rejection", item + "=" + str(self.mon.pk))
            self.assertEqual(self.snapshot(), before)
            PlacementService(self.storage).to_party(self.mon, slot=3)
            PlacementService(self.storage).reserve_for_fusion(self.mon)
            before = self.snapshot()
            for target in ("fusion", str(self.mon.pk)):
                self.command(item + "=" + target)
                self.assertEqual(self.snapshot(), before)
            PlacementService(self.storage).return_from_fusion(self.mon, preferred_slot=3)

    def test_ambiguity_gapped_slots_foreign_and_stale_owner(self):
        """Never pick another same-name target or trust stale owner/EV fields."""
        self.create_mon(slot=6)
        other = ObjectDB.objects.create(db_key="training-foreign-" + uuid4().hex)
        trainer = Trainer.objects.create(user=other, trainer_number=Trainer.objects.count() + 1)
        foreign = create_owned_pokemon("Eevee", trainer, 20)
        self.prepare("Protein")
        self.give("Protein")
        before = self.snapshot()
        for target in ("Mew", "1", str(foreign.pk), "Missing"):
            self.command("Protein=" + target)
            self.assertEqual(self.snapshot(), before)
        self.state(trainer_id=trainer.pk)
        before = self.snapshot()
        self.command("Protein=3")
        self.assertEqual(self.snapshot(), before)

    def test_fresh_ev_caps_override_stale_cache(self):
        """Do not grant a free over-cap increase from an old Pokemon instance."""
        self.prepare("Protein", evs=[0] * 6)
        self.give("Protein")
        self.state(evs=[0, 252, 0, 0, 0, 0])
        before = self.snapshot()
        self.command("Protein=3")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.mon.evs, [0, 252, 0, 0, 0, 0])

    def test_battle_locks_selectors_syntax_and_excluded_items(self):
        """Keep training field-only, single-target and separate from other gaps."""
        for item in TRAINING:
            self.prepare(item)
            self.give(item)
            before = self.snapshot()
            self.character.db.battle_lock = "field-training-fixture"
            self.command(item + "=3")
            self.assertIsNone(FieldTrainingUse(self.player).use(item, "3"))
            self.assertEqual(self.snapshot(), before)
            self.character.db.battle_lock = None
            self.player.ndb.battle_instance = object()
            self.command(item + "=3")
            self.assertEqual(self.snapshot(), before)
            self.player.ndb.battle_instance = None
            for target in ("3/1", "party"):
                self.command(item + "=" + target)
                self.assertEqual(self.snapshot(), before)
        for args in ("Protein", "Protein=", "HP=3", "Health=3", "Protein=Iron"):
            before = self.snapshot()
            self.command(args)
            self.assertEqual(self.snapshot(), before)
        for item in ("Pretty Feather", "Bottle Cap", "Ability Capsule", "Ability Patch", "X Attack"):
            self.give(item)
            before = self.snapshot()
            self.command(item + "=3")
            self.assertEqual(self.snapshot(), before)
            self.assertFalse(FieldTrainingUse.supports(item))

    def test_failed_or_partial_debit_rolls_back_each_item(self):
        """A writer that reports failure after real inventory SQL must roll back."""
        original = Trainer.remove_item

        def partial(trainer, *args):
            """Inject the failure after the real debit, including cache callbacks."""
            original(trainer, *args)
            return False

        for item in TRAINING:
            for debit in (lambda *args: False, partial):
                self.prepare(item)
                self.give(item)
                before = self.snapshot()
                with patch.object(Trainer, "remove_item", debit):
                    self.record("failed-training-debit", item + "=3")
                self.assertEqual(self.snapshot(), before)

    def test_post_sql_save_failure_rolls_back_evs_hp_bag_and_cache(self):
        """Every item rolls back after the actual Pokemon UPDATE has occurred."""
        original = OwnedPokemon.save

        def fail_after_save(pokemon, *args, **kwargs):
            """Preserve the real SQL effect, then fail within the outer transaction."""
            original(pokemon, *args, **kwargs)
            raise RuntimeError("injected training save failure")

        for item in TRAINING:
            self.prepare(item)
            self.give(item)
            before = self.snapshot()
            stats = get_stats(self.fresh())
            with patch.object(OwnedPokemon, "save", fail_after_save):
                with self.assertRaisesRegex(RuntimeError, "injected training"):
                    self.command(item + "=3")
            self.assertEqual(self.snapshot(), before)
            self.assertEqual(get_stats(self.mon), stats)
            self.assertEqual(self.mon.current_hp, before["pokemon"]["current_hp"])

    def race(self, *actions):
        """Use separate synchronized PostgreSQL connections for genuine contention."""
        from django.db import close_old_connections
        barrier = Barrier(len(actions))

        def run(action):
            """Isolate connection lifetime on each worker."""
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return action()
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            return list(pool.map(run, actions))

    def test_last_copy_contention_for_all_twelve(self):
        """A single copy funds exactly one increase for either family."""
        for item, (index, amount) in TRAINING.items():
            self.prepare(item, evs=[0] * 6)
            self.give(item)
            self.race(lambda: self.command(item + "=3"), lambda: self.command(item + "=3"))
            expected = [0] * 6
            expected[index] = amount
            self.assertEqual(self.snapshot()["pokemon"]["evs"], expected)
            self.assertEqual(self.trainer.get_item_quantity(item), 0)

    def test_competing_stats_share_fresh_total_capacity(self):
        """Different vitamins/feathers cannot both claim the final EV budget."""
        for left, right in (("Protein", "Iron"), ("Muscle Feather", "Resist Feather"), ("Protein", "Resist Feather")):
            self.prepare(left, evs=[252, 0, 0, 252, 5, 0])
            self.give(left)
            self.give(right)
            quantities = sum(self.trainer.get_item_quantity(item) for item in (left, right))
            self.race(lambda: self.command(left + "=3"), lambda: self.command(right + "=3"))
            evs = self.snapshot()["pokemon"]["evs"]
            self.assertEqual(sum(evs), 510)
            self.assertIn((evs[1], evs[2]), ((1, 0), (0, 1)))
            self.assertEqual(sum(self.trainer.get_item_quantity(item) for item in (left, right)), quantities - 1)

    def test_competing_same_stat_does_not_spend_capped_second_item(self):
        """Two stocked commands at a stat cap yield only one useful increase."""
        self.prepare("Protein", evs=[0, 251, 0, 0, 0, 0])
        self.give("Protein", 2)
        self.race(lambda: self.command("Protein=3"), lambda: self.command("Protein=3"))
        self.assertEqual(self.snapshot()["pokemon"]["evs"], [0, 252, 0, 0, 0, 0])
        self.assertEqual(self.trainer.get_item_quantity("Protein"), 1)

    def test_last_copy_cannot_train_two_different_party_members(self):
        """Shared inventory locking also serializes uses on distinct targets."""
        other = self.create_mon(slot=6)
        self.prepare("Protein", evs=[0] * 6)
        self.give("Protein")
        self.race(lambda: self.command("Protein=3"), lambda: self.command("Protein=6"))
        rows = [self.snapshot(pokemon)["pokemon"] for pokemon in (self.mon, other)]
        self.assertEqual(sorted(row["evs"][1] for row in rows), [0, 10])
        self.assertEqual(self.trainer.get_item_quantity("Protein"), 0)


TRAINING = {
    "HP Up": (0, 10), "Protein": (1, 10), "Iron": (2, 10),
    "Calcium": (3, 10), "Zinc": (4, 10), "Carbos": (5, 10),
    "Health Feather": (0, 1), "Muscle Feather": (1, 1), "Resist Feather": (2, 1),
    "Genius Feather": (3, 1), "Clever Feather": (4, 1), "Swift Feather": (5, 1),
}
STATS = ("hp", "attack", "defense", "special_attack", "special_defense", "speed")


def add_flow(item):
    """Count each real item as one discover/use/reload acceptance case."""
    def case(self):
        """Run the ordinary-player flow for this named vitamin or feather."""
        self.field_flow(item)
    setattr(FieldTrainingCases, "test_player_flow_" + item.lower().replace(" ", "_"), case)


for training_item in TRAINING:
    add_flow(training_item)


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
        from evennia.objects.models import ObjectDB
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon, get_max_hp, get_stats
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot, MovePPBoost, MovesetSlot, PokemonLearnedMove
        from pokemon.models.storage import PokemonPlacement, StorageBox, UserStorage
        from pokemon.models.trainer import Trainer, InventoryEntry
        from pokemon.services.field_items import FieldMedicineUse
        from pokemon.services.field_training import FieldTrainingUse
        from pokemon.services.placement import PlacementService
        from pokemon.user import User
        COMMANDS = {"use": CmdUseItem, "inventory": CmdInventory, "party": CmdSheetPokemon,
                    "deposit": CmdDepositPokemon, "hold": CmdSetHoldItem}
        try:
            result = unittest.main(verbosity=2, exit=False).result
        finally:
            destination = os.environ.get("PF2_TRAINING_EVIDENCE")
            if destination:
                Path(destination).write_text(json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())

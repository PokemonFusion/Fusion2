"""Prove ordinary legacy berry commands with real disposable PostgreSQL rows."""

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

LEGACY = {
    "Berry": ("hp", 10), "Gold Berry": ("hp", 30),
    "Burnt Berry": ("status", "frz"), "Ice Berry": ("status", "brn"),
    "Mint Berry": ("status", "slp"), "Miracle Berry": ("status", "tox"),
    "Mystery Berry": ("pp", 5), "PRZ Cure Berry": ("status", "par"),
    "PSN Cure Berry": ("status", "psn"),
}


class BerryPlayer(PlayerView):
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


class LegacyBerryCases(unittest.TestCase):
    """Check all nine field routes, canonical targets, persistence and atomic use."""

    def setUp(self):
        """Create a tagged ordinary owner with a genuinely gapped party."""
        self.character = ObjectDB.objects.create(db_key="legacy-berry-767-" + uuid4().hex, db_typeclass_path="pokemon.user.User")
        self.trainer, _ = Trainer.objects.get_or_create(user=self.character, defaults={"trainer_number": Trainer.objects.count() + 1})
        self.storage, _ = UserStorage.objects.get_or_create(user=self.character)
        StorageBox.objects.create(storage=self.storage, name="Legacy Berry Box")
        self.player = BerryPlayer(self.character, self.trainer, self.storage)
        self.player.pk = self.character.pk
        self.mon = self.create_mon()
        self.mon.activemoveslot_set.filter(slot=2).update(slot=4)

    def tearDown(self):
        """Release any real menu on this disposable transport."""
        menu = self.player.ndb._evmenu
        if menu:
            menu.close_menu()

    def create_mon(self, slot=3, species="Mew", level=50):
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

    def prepare(self, item):
        """Set meaningful saved conditions while retaining stale cached fields."""
        effect, value = LEGACY[item]
        self.state(current_hp=1 if effect == "hp" else 12, status=value if effect == "status" else "psn",
                   sleep_turns=2 if value == "slp" else None, held_item=item, friendship=203,
                   flags=["ordinary-legacy-berry-fixture"])
        self.mon.activemoveslot_set.update(current_pp=0)
        return effect, value

    def pp(self):
        """Read real active slots, including the gap between 1 and 4."""
        return list(self.mon.activemoveslot_set.order_by("slot").values_list("current_pp", flat=True))

    def assert_effect(self, item, *, remaining=0):
        """Check exact useful effects independently from field-service code."""
        effect, value = LEGACY[item]
        row = self.snapshot()["pokemon"]
        self.assertEqual(row["held_item"], item)
        self.assertEqual(row["friendship"], 203)
        self.assertEqual(row["flags"], ["ordinary-legacy-berry-fixture"])
        self.assertEqual(self.trainer.get_item_quantity(item), remaining)
        if effect == "hp":
            self.assertEqual((row["current_hp"], row["status"]), (1 + value, "psn"))
        elif effect == "status":
            self.assertEqual((row["current_hp"], row["status"], row["sleep_turns"]), (12, "", None))
        else:
            self.assertEqual((row["current_hp"], row["status"]), (12, "psn"))
            self.assertEqual(self.pp(), [5, 0])

    def field_flow(self, item):
        """Inventory/party discovery, real use and connection reload for one item."""
        from django.db import connections

        self.prepare(item)
        self.give(item)
        self.assertIn(item, self.command("", "inventory"))
        self.assertIn(str(self.mon.pk), self.command("3", "party"))
        before = self.snapshot()
        self.record("ordinary-legacy-use-" + item, item + "=3")
        self.assertTrue(self.player.messages[-1].startswith("Used "), self.player.messages[-1])
        self.assert_effect(item)
        after = self.snapshot()
        for field in ("placement", "learned", "sets", "boosts"):
            self.assertEqual(after[field], before[field])
        connections.close_all()
        OwnedPokemon.flush_cached_instance(self.mon)
        self.assert_effect(item)

    def test_names_and_inventory_aliases_are_exact_normalized_matches(self):
        """All nine legacy display spellings debit existing alias rows correctly."""
        for item in LEGACY:
            with self.subTest(item=item):
                self.prepare(item)
                InventoryEntry.objects.create(owner=self.trainer, item_name=item.upper(), quantity=1)
                query = item.upper().replace(" ", "-")
                self.record("normalized-inventory-alias", query + "=" + str(self.mon.pk))
                self.assert_effect(item)
        self.give("Gold Berry")
        before = self.snapshot()
        for args in ("Gold=3", "Mystery=3", "PRZ Cure=3"):
            self.command(args)
            self.assertEqual(self.snapshot(), before)

    def test_hp_amounts_caps_above_held_threshold_and_no_revival(self):
        """Berry/Gold restore fixed HP, cap at calculated maximum and never revive."""
        maximum = get_max_hp(self.mon)
        for item in ("Berry", "Gold Berry"):
            self.give(item, 3)
            self.state(current_hp=maximum - 1)
            self.record("hp-cap-above-held-threshold", item + "=3")
            self.assertEqual(self.snapshot()["pokemon"]["current_hp"], maximum)
            for hp in (maximum, 0):
                self.state(current_hp=hp)
                before = self.snapshot()
                self.record("hp-no-effect", item + "=3")
                self.assertEqual(self.snapshot(), before)

    def test_status_matrix_and_wrong_status_no_effect(self):
        """Review every persistent condition, including Burnt/Ice and poison/toxic."""
        mapping = {"Burnt Berry": {"frz"}, "Ice Berry": {"brn"}, "Mint Berry": {"slp"},
                   "Miracle Berry": {"par", "slp", "psn", "tox", "brn", "frz"},
                   "PRZ Cure Berry": {"par"}, "PSN Cure Berry": {"psn", "tox"}}
        for item, cures in mapping.items():
            for status in ("", "par", "slp", "psn", "tox", "brn", "frz"):
                with self.subTest(item=item, status=status):
                    self.state(current_hp=12, status=status, sleep_turns=2 if status == "slp" else None)
                    self.give(item)
                    before = self.snapshot()
                    quantity = self.trainer.get_item_quantity(item)
                    self.command(item + "=3")
                    if status in cures:
                        row = self.snapshot()["pokemon"]
                        self.assertEqual((row["status"], row["sleep_turns"], row["current_hp"]), ("", None, 12))
                        self.assertEqual(self.trainer.get_item_quantity(item), quantity - 1)
                    else:
                        self.assertEqual(self.snapshot(), before)

    def test_mystery_real_move_slot_name_default_and_boosted_cap(self):
        """Share PP restoration with Leppa; never compact a gapped active slot."""
        self.prepare("Mystery Berry")
        water = self.mon.activemoveslot_set.get(slot=4)
        MovePPBoost.objects.create(pokemon=self.mon, move=water.move, bonus_pp=15)
        self.give("Mystery Berry", 7)
        self.record("mystery-normalized-move-name", "Mystery Berry=3/WATER GUN")
        self.assertEqual(self.pp(), [0, 5])
        self.record("mystery-real-slot", "Mystery Berry=3/4")
        self.assertEqual(self.pp(), [0, 10])
        self.mon.activemoveslot_set.filter(slot=4).update(current_pp=39)
        self.record("mystery-boosted-cap", "Mystery Berry=3/4")
        self.assertEqual(self.pp(), [0, 40])
        for selection in ("4", "2", "Water", "Unknown"):
            before = self.snapshot()
            self.command("Mystery Berry=3/" + selection)
            self.assertEqual(self.snapshot(), before)
        self.record("mystery-first-depleted", "Mystery Berry=3")
        self.assertEqual(self.pp(), [5, 40])
        self.assertEqual(self.trainer.get_item_quantity("Mystery Berry"), 3)

    def test_all_legacy_status_and_pp_berries_are_ineffective_when_fainted(self):
        """None of the nine recovery equivalents can revive a target."""
        for item in LEGACY:
            self.prepare(item)
            self.state(current_hp=0)
            self.give(item)
            before = self.snapshot()
            self.command(item + "=3")
            self.assertEqual(self.snapshot(), before)

    def test_egg_box_and_inactive_fusion_guards_apply_to_all_nine(self):
        """Reuse fresh canonical eligibility for every new allowlist entry."""
        for item in LEGACY:
            self.prepare(item)
            self.give(item)
            self.state(is_egg=True)
            before = self.snapshot()
            self.command(item + "=3")
            self.assertEqual(self.snapshot(), before)
            self.state(is_egg=False)
            self.assertIn("deposited", self.command(str(self.mon.pk), "deposit"))
            before = self.snapshot()
            self.record("normal-deposit-ineligible", item + "=" + str(self.mon.pk))
            self.assertEqual(self.snapshot(), before)
            PlacementService(self.storage).to_party(self.mon, slot=3)
            PlacementService(self.storage).reserve_for_fusion(self.mon)
            before = self.snapshot()
            for target in ("fusion", str(self.mon.pk)):
                self.command(item + "=" + target)
                self.assertEqual(self.snapshot(), before)
            PlacementService(self.storage).return_from_fusion(self.mon, preferred_slot=3)

    def test_current_fusion_and_name_uuid_legacy_syntax_routes(self):
        """All items can feed the actual current Fusion; normal target syntax stays."""
        PlacementService(self.storage).reserve_for_fusion(self.mon)
        self.character.db.fusion_id = str(self.mon.pk)
        for index, item in enumerate(LEGACY):
            self.prepare(item)
            self.give(item)
            self.record("current-fusion-legacy-berry", item + "=" + ("fusion", "self", "me")[index % 3])
            self.assert_effect(item)
        PlacementService(self.storage).return_from_fusion(self.mon, preferred_slot=3)
        self.character.db.fusion_id = None
        for args in ("Berry=Mew", "3=Berry", "Berry=" + str(self.mon.pk)):
            self.prepare("Berry")
            self.give("Berry")
            self.command(args)
            self.assert_effect("Berry")

    def test_ambiguous_and_foreign_targets_rejected(self):
        """Do not silently choose a duplicate species/nickname or foreign UUID."""
        self.create_mon(slot=6)
        other = ObjectDB.objects.create(db_key="legacy-foreign-" + uuid4().hex)
        trainer = Trainer.objects.create(user=other, trainer_number=Trainer.objects.count() + 1)
        foreign = create_owned_pokemon("Eevee", trainer, 20)
        self.prepare("Berry")
        self.give("Berry")
        before = self.snapshot()
        for target in ("Mew", str(foreign.pk), "1", "Missing"):
            self.command("Berry=" + target)
            self.assertEqual(self.snapshot(), before)
        self.command("Berry=3")
        self.assert_effect("Berry")

    def test_stale_owner_hp_status_and_inventory_never_bypass_fresh_checks(self):
        """Saved values override cached Pokemon and caller trainer references."""
        self.prepare("Berry")
        self.give("Berry")
        self.state(current_hp=get_max_hp(self.mon))
        before = self.snapshot()
        self.command("Berry=3")
        self.assertEqual(self.snapshot(), before)
        other = ObjectDB.objects.create(db_key="changed-legacy-owner-" + uuid4().hex)
        trainer = Trainer.objects.create(user=other, trainer_number=Trainer.objects.count() + 1)
        self.state(current_hp=1, trainer_id=trainer.pk)
        before = self.snapshot()
        self.command("Berry=3")
        self.assertEqual(self.snapshot(), before)

    def test_battle_missing_stock_bad_syntax_and_move_selector_guards(self):
        """No berry use bypasses battle locks or accepts a meaningless move."""
        for item in LEGACY:
            self.prepare(item)
            before = self.snapshot()
            self.command(item + "=3")
            self.assertEqual(self.snapshot(), before)
            self.give(item)
            before = self.snapshot()
            self.character.db.battle_lock = "legacy-berry-fixture"
            self.command(item + "=3")
            self.assertIsNone(FieldBerryUse(self.player).use(item, "3"))
            self.assertEqual(self.snapshot(), before)
            self.character.db.battle_lock = None
            self.player.ndb.battle_instance = object()
            self.command(item + "=3")
            self.assertEqual(self.snapshot(), before)
            self.player.ndb.battle_instance = None
            if item != "Mystery Berry":
                self.command(item + "=3/1")
                self.assertEqual(self.snapshot(), before)
            self.trainer.remove_item(item)
        for args in ("Berry", "Berry=", "Mystery Berry=3/", "Mystery Berry=/4", "Berry=Potion"):
            before = self.snapshot()
            self.command(args)
            self.assertEqual(self.snapshot(), before)

    def test_bitter_persim_combat_and_contest_berries_remain_unallowlisted(self):
        """Confusion is a battle volatile, not a saved field status to invent."""
        for item in ("Bitter Berry", "Persim Berry", "Enigma Berry", "Chilan Berry", "Liechi Berry", "Razz Berry", "Bluk Berry"):
            self.give(item)
            before = self.snapshot()
            self.command(item + "=3")
            self.assertEqual(self.snapshot(), before)
            self.assertFalse(FieldBerryUse.supports(item))
            self.assertIn("not usable outside battle", self.player.messages[-1])

    def test_bag_use_keeps_actual_held_copy_and_held_only_copy_cannot_be_spent(self):
        """Real +hold and +use consume separate copies, then the held copy returns."""
        self.give("Berry", 2)
        self.assertIn("now holding Berry", self.command("3=Berry", "hold"))
        self.state(current_hp=1)
        self.record("bag-and-held-independent", "Berry=3")
        self.assertEqual(self.snapshot()["pokemon"]["held_item"], "Berry")
        self.assertEqual(self.trainer.get_item_quantity("Berry"), 0)
        before = self.snapshot()
        self.command("Berry=3")
        self.assertEqual(self.snapshot(), before)
        self.assertIn("returned to your inventory", self.command("3=", "hold"))
        self.assertEqual(self.trainer.get_item_quantity("Berry"), 1)

    def test_false_and_partial_debit_roll_back_all_nine(self):
        """A failed debit after real inventory SQL cannot leak stock or effects."""
        original = Trainer.remove_item

        def partial_failure(trainer, *args):
            """Perform the real write, then report an injected failure."""
            original(trainer, *args)
            return False

        for item in LEGACY:
            for debit in (lambda *args: False, partial_failure):
                self.prepare(item)
                self.give(item)
                before = self.snapshot()
                with patch.object(Trainer, "remove_item", debit):
                    self.record("failed-debit", item + "=3")
                self.assertEqual(self.snapshot(), before)

    def test_failure_after_real_hp_or_status_write_rolls_back_bag_and_cache(self):
        """Every non-PP legacy effect is atomic with its real inventory debit."""
        original = OwnedPokemon.save

        def fail_after_save(pokemon, *args, **kwargs):
            """Fail after the actual Pokemon UPDATE, not instead of the effect."""
            original(pokemon, *args, **kwargs)
            raise RuntimeError("injected legacy save failure")

        for item, (effect, _) in LEGACY.items():
            if effect == "pp":
                continue
            self.prepare(item)
            self.give(item)
            before = self.snapshot()
            with patch.object(OwnedPokemon, "save", fail_after_save):
                with self.assertRaisesRegex(RuntimeError, "injected"):
                    self.command(item + "=3")
            self.assertEqual(self.snapshot(), before)
            self.assertEqual(self.mon.current_hp, before["pokemon"]["current_hp"])
            self.assertEqual(self.mon.status, before["pokemon"]["status"])

    def test_mystery_pp_save_failure_rolls_back_slot_debit_and_cache(self):
        """Use the same transactional PP writer and propagate post-write failures."""
        self.prepare("Mystery Berry")
        self.give("Mystery Berry")
        before = self.snapshot()
        original = ActiveMoveslot.save

        def fail_after_save(slot, *args, **kwargs):
            """Keep actual current-PP SQL before injecting the fault."""
            original(slot, *args, **kwargs)
            raise RuntimeError("injected PP save failure")

        with patch.object(ActiveMoveslot, "save", fail_after_save):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                self.command("Mystery Berry=3/4")
        self.assertEqual(self.snapshot(), before)

    def race(self, *actions):
        """Compete using independent PostgreSQL connections and real commands."""
        from django.db import close_old_connections

        barrier = Barrier(len(actions))

        def run(action):
            """Close each worker's database connection after synchronized input."""
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return action()
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            return list(pool.map(run, actions))

    def test_competing_final_copy_is_one_effect_for_every_legacy_berry(self):
        """One final copy cannot fund two healing, status or PP effects."""
        for item in LEGACY:
            self.prepare(item)
            self.give(item)
            self.race(lambda: self.command(item + "=3"), lambda: self.command(item + "=3"))
            self.assert_effect(item)

    def test_competing_terminal_recovery_rechecks_no_effect_without_second_debit(self):
        """Two copies at the HP cap buy only one useful feed."""
        self.state(current_hp=get_max_hp(self.mon) - 1)
        self.give("Gold Berry", 2)
        self.race(lambda: self.command("Gold Berry=3"), lambda: self.command("Gold Berry=3"))
        self.assertEqual(self.snapshot()["pokemon"]["current_hp"], get_max_hp(self.mon))
        self.assertEqual(self.trainer.get_item_quantity("Gold Berry"), 1)


def add_flow(item):
    """Count each named legacy item as its own ordinary-command acceptance case."""
    def case(self):
        """Run the per-item discovery/use/reload route."""
        self.field_flow(item)
    setattr(LegacyBerryCases, "test_player_flow_" + item.lower().replace(" ", "_"), case)


for legacy_item in LEGACY:
    add_flow(legacy_item)


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
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon, get_max_hp
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot, MovePPBoost, MovesetSlot, PokemonLearnedMove
        from pokemon.models.storage import PokemonPlacement, StorageBox, UserStorage
        from pokemon.models.trainer import Trainer, InventoryEntry
        from pokemon.services.field_berries import FieldBerryUse
        from pokemon.services.placement import PlacementService
        from pokemon.user import User
        COMMANDS = {"use": CmdUseItem, "inventory": CmdInventory, "party": CmdSheetPokemon, "deposit": CmdDepositPokemon, "hold": CmdSetHoldItem}
        try:
            result = unittest.main(verbosity=2, exit=False).result
        finally:
            destination = os.environ.get("PF2_LEGACY_BERRY_EVIDENCE")
            if destination:
                Path(destination).write_text(json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())

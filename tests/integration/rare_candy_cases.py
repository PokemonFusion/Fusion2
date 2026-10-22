"""Prove ordinary Rare Candy commands with real disposable PostgreSQL rows."""

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


class CandyPlayer(PlayerView):
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


class RareCandyCases(unittest.TestCase):
    """Check targeting, atomic progression, learning, state and contention."""

    def setUp(self):
        """Create a tagged ordinary owner with a genuinely gapped party."""
        self.character = ObjectDB.objects.create(db_key="rare-candy-764-" + uuid4().hex)
        self.trainer = Trainer.objects.create(user=self.character, trainer_number=Trainer.objects.count() + 1)
        self.storage = UserStorage.objects.create(user=self.character)
        StorageBox.objects.create(storage=self.storage, name="Candy Box")
        self.player = CandyPlayer(self.character, self.trainer, self.storage)
        self.player.pk = self.character.pk
        self.mon = self.create_mon()

    def tearDown(self):
        """Release any real move prompt on this disposable transport."""
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
        """Read exact persisted rows, including moves that learning can change."""
        identifier = (pokemon or self.mon).pk
        return {
            "pokemon": OwnedPokemon.objects.filter(pk=identifier).values().get(),
            "placement": list(PokemonPlacement.objects.filter(pokemon_id=identifier).values()),
            "inventory": list(self.trainer.list_inventory().values("item_name", "quantity")),
            "learned": list(PokemonLearnedMove.objects.filter(pokemon_id=identifier).order_by("move_id").values()),
            "active": list(ActiveMoveslot.objects.filter(pokemon_id=identifier).order_by("slot").values()),
            "sets": list(MovesetSlot.objects.filter(moveset__pokemon_id=identifier).order_by("pk").values()),
        }

    def give(self, amount=2):
        """Fixture setup grants bag stock separately from ordinary acceptance."""
        self.trainer.add_item("Rare Candy", amount)

    def record(self, label, args, pokemon=None):
        """Retain ordinary input/output and independent SQL before/after proof."""
        before, start = self.snapshot(pokemon), len(self.player.messages)
        self.command(args)
        EVIDENCE.append({"label": label, "command": "+use " + args, "before": before,
                         "after": self.snapshot(pokemon), "messages": self.player.messages[start:]})

    def test_discover_use_reload_and_intentional_second_use(self):
        """Inventory/party discovery leads to two legitimate, paid level gains."""
        self.give()
        self.assertIn("Rare Candy", self.command("", "inventory"))
        self.assertIn(str(self.mon.pk), self.command("3", "party"))
        self.record("canonical-slot", "Rare Candy=3")
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("level", flat=True).get(), 51)
        self.player = CandyPlayer(self.character, self.trainer, self.storage)
        self.player.pk = self.character.pk
        self.record("full-id-after-transport-rebuild", "Rare Candy=" + str(self.mon.pk))
        self.assertEqual(self.mon.total_exp, exp_for_level(52))
        self.assertEqual(self.trainer.get_item_quantity("Rare Candy"), 0)
        self.assertIn("grew to level 52", self.player.messages[-1])

    def test_names_punctuation_and_target_first_compatibility(self):
        """Complete names/aliases and legacy syntax still reach one safe use."""
        self.state(nickname="Candy Buddy")
        self.give(3)
        for args in ("RareCandy=Candy Buddy", "3=Rare Candy", "Rare Candy=Mew"):
            self.record("name-or-compatible-syntax", args)
        self.assertEqual(self.mon.level, 53)
        self.assertEqual(self.trainer.get_item_quantity("Rare Candy"), 0)

    def test_partial_exp_and_unrelated_saved_state_preserved(self):
        """Gain exactly one level from partial EXP without curing or healing."""
        self.state(total_exp=exp_for_level(50) + 10, current_hp=7, status="slp", sleep_turns=2,
                   friendship=204, flags=["ordinary-test-flag"], held_item="Everstone")
        self.give(1)
        before = self.snapshot()
        self.record("partial-exp-state-preservation", "Rare Candy=3")
        after = self.snapshot()
        expected = dict(before["pokemon"], level=51, total_exp=exp_for_level(51))
        self.assertEqual(after["pokemon"], expected)
        self.assertEqual(after["placement"], before["placement"])
        self.assertEqual(after["active"], before["active"])
        self.assertGreater(get_max_hp(self.mon), 7)

    def test_fainted_target_stays_fainted(self):
        """Preserve PF2's current Rare Candy HP policy, including zero HP."""
        self.state(current_hp=0)
        self.give(1)
        self.command("Rare Candy=3")
        self.assertEqual((self.mon.level, self.mon.current_hp), (51, 0))

    def test_duplicate_names_rejected_and_slot_can_disambiguate(self):
        """Two Buddy members never silently choose the first match."""
        other = self.create_mon(slot=6)
        self.state(nickname="Buddy")
        self.state(other, nickname="Buddy")
        self.give()
        before = self.snapshot()
        self.record("ambiguous-name", "Rare Candy=Buddy")
        self.assertEqual(self.snapshot(), before)
        self.assertIn("ambiguous", self.player.messages[-1])
        self.command("Rare Candy=6")
        self.assertEqual(OwnedPokemon.objects.filter(pk=other.pk).values_list("level", flat=True).get(), 51)
        self.assertEqual(self.mon.level, 50)

    def test_egg_and_stale_cached_egg_rejected(self):
        """The service reads stored egg state rather than an old Python field."""
        self.give()
        self.state(is_egg=True)
        self.assertFalse(self.mon.is_egg)
        before = self.snapshot()
        self.record("egg-rejected", "Rare Candy=3")
        self.assertEqual(self.snapshot(), before)
        self.assertIn("eggs", self.player.messages[-1])

    def test_normal_deposit_blocks_later_use(self):
        """A normal box deposit removes both slot and full-ID eligibility."""
        self.give()
        self.assertIn("deposited", self.command(str(self.mon.pk), "deposit"))
        before = self.snapshot()
        for target in ("3", str(self.mon.pk), "Mew"):
            self.command("Rare Candy=" + target)
            self.assertEqual(self.snapshot(), before)

    def test_current_fusion_aliases_and_id(self):
        """Only this character's actual current reserved Fusion can grow."""
        PlacementService(self.storage).reserve_for_fusion(self.mon)
        self.character.db.fusion_id = str(self.mon.pk)
        self.give(4)
        for target in ("fusion", "self", "me", str(self.mon.pk)):
            self.record("current-fusion", "Rare Candy=" + target)
        self.assertEqual(self.mon.level, 54)
        self.assertEqual(self.trainer.get_item_quantity("Rare Candy"), 0)

    def test_inactive_fusion_and_missing_targets_rejected(self):
        """Full IDs and stale selector objects cannot bypass reservation rules."""
        self.give()
        service = FieldRareCandyUse(self.player)
        PlacementService(self.storage).reserve_for_fusion(self.mon)
        before = self.snapshot()
        for target in (str(self.mon.pk), "fusion", "self", "me", "1", "Unknown"):
            self.command("Rare Candy=" + target)
            self.assertEqual(self.snapshot(), before)
        with self.assertRaises(FieldMedicineError):
            service.use("Rare Candy", "3")

    def test_foreign_id_and_changed_owner_rejected(self):
        """Fresh ownership beats a stale model and another character's UUID."""
        character = ObjectDB.objects.create(db_key="foreign-candy-" + uuid4().hex)
        trainer = Trainer.objects.create(user=character, trainer_number=Trainer.objects.count() + 1)
        foreign = create_owned_pokemon("Mew", trainer, 50)
        self.give()
        before = self.snapshot()
        self.command("Rare Candy=" + str(foreign.pk))
        self.assertEqual(self.snapshot(), before)
        self.state(trainer_id=trainer.pk)
        before = self.snapshot()
        self.command("Rare Candy=3")
        self.assertEqual(self.snapshot(), before)

    def test_resolved_target_is_revalidated_before_effect(self):
        """A placement change after selection is caught by the locked row check."""
        self.give()
        original = FieldRareCandyUse._targets

        def move_after_resolving(service, storage, query, item):
            """Model a stale selection without replacing eligibility/effect code."""
            result = original(service, storage, query, item)
            PlacementService(storage).to_box(self.mon)
            return result

        before = self.snapshot()
        with patch.object(FieldRareCandyUse, "_targets", move_after_resolving):
            self.command("Rare Candy=3")
        self.assertEqual(self.snapshot(), before)
        self.assertIn("no longer", self.player.messages[-1])

    def test_battle_guards_at_command_and_locked_service(self):
        """Both persisted battle lock and live session reference block use."""
        self.give()
        service = FieldRareCandyUse(self.player)
        before = self.snapshot()
        for persisted in (True, False):
            self.character.db.battle_lock = "fixture-battle" if persisted else None
            self.player.ndb.battle_instance = None if persisted else object()
            self.command("Rare Candy=3")
            self.assertIsNone(service.use("Rare Candy", "3"))
            self.assertEqual(self.snapshot(), before)

    def test_locked_service_rechecks_battle_after_command_guard(self):
        """A battle starting while use waits for the lock cannot be bypassed."""
        self.give()
        before = self.snapshot()
        with patch("pokemon.services.field_items.require_no_battle_lock", return_value=False):
            self.command("Rare Candy=3")
        self.assertEqual(self.snapshot(), before)

    def test_level_cap_missing_stock_and_bad_syntax_do_not_consume(self):
        """Reject no-effect, malformed and unknown uses before any writes."""
        before = self.snapshot()
        self.command("Rare Candy=3")
        self.assertEqual(self.snapshot(), before)
        self.give()
        for args in ("Rare Candy", "Rare Candy=", "Rare Candy=3/Tackle", "Rare Candy=1", "Rare Candy=Potion"):
            before = self.snapshot()
            self.command(args)
            self.assertEqual(self.snapshot(), before)
        self.state(level=100, total_exp=exp_for_level(100))
        before = self.snapshot()
        self.record("level-cap", "Rare Candy=3")
        self.assertEqual(self.snapshot(), before)
        self.assertIn("level 100", self.player.messages[-1])

    def test_invalid_saved_progression_fails_without_repair_or_debit(self):
        """Do not silently rewrite inconsistent stored level/EXP."""
        self.give()
        self.state(total_exp=0)
        before = self.snapshot()
        self.command("Rare Candy=3")
        self.assertEqual(self.snapshot(), before)
        self.assertIn("Invalid saved", self.player.messages[-1])

    def test_failed_debit_does_not_grant_a_level(self):
        """The audit's free-level reproduction now rolls back completely."""
        self.give()
        before = self.snapshot()
        with patch.object(Trainer, "remove_item", return_value=False):
            self.record("failed-debit", "Rare Candy=3")
        self.assertEqual(self.snapshot(), before)
        self.assertNotIn("grew to level", self.player.messages[-1])

    def test_partial_debit_failure_rolls_back_inventory_too(self):
        """A failed debit after a real write must not consume stock either."""
        self.give()
        before = self.snapshot()
        original = Trainer.remove_item

        def fail_after_debit(trainer, *args):
            """Keep the real inventory write, then inject its failure result."""
            original(trainer, *args)
            return False

        with patch.object(Trainer, "remove_item", fail_after_debit):
            self.command("Rare Candy=3")
        self.assertEqual(self.snapshot(), before)

    def test_failure_after_level_save_restores_rows_caches_and_stock(self):
        """Failure after SQL save rolls back EXP, level, debit and model cache."""
        self.give()
        before = self.snapshot()
        original = OwnedPokemon.save

        def fail_after_save(pokemon, *args, **kwargs):
            """Inject a real post-write failure only for this Pokemon's gain."""
            original(pokemon, *args, **kwargs)
            if pokemon.pk == self.mon.pk and pokemon.level > 50:
                raise RuntimeError("injected after level save")

        with patch.object(OwnedPokemon, "save", fail_after_save):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                self.command("Rare Candy=3")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual((self.mon.level, self.mon.total_exp), (50, exp_for_level(50)))
        self.assertFalse(any("grew to level" in m for m in self.player.messages))

    def learning_mon(self, full=False):
        """Use Bulbasaur's real level-3 Vine Whip rule for learning checks."""
        pokemon = create_owned_pokemon(
            "Bulbasaur", self.trainer, 2, nature="Hardy", ivs=[0] * 6, evs=[0] * 6,
            active_move_names=["Tackle", "Growl", "Protect", "Substitute"] if full else ["Tackle", "Growl"],
        )
        PlacementService(self.storage).to_party(pokemon, slot=6)
        return pokemon

    def test_level_up_move_is_learned_in_same_transaction(self):
        """Normal learning still persists with a paid level gain."""
        pokemon = self.learning_mon()
        self.give(1)
        self.record("level-up-learning", "Rare Candy=6", pokemon)
        self.assertEqual(OwnedPokemon.objects.filter(pk=pokemon.pk).values_list("level", flat=True).get(), 3)
        self.assertTrue(pokemon.learned_moves.filter(name__iexact="Vinewhip").exists())
        self.assertTrue(pokemon.activemoveslot_set.filter(move__name__iexact="Vinewhip").exists())
        self.assertTrue(any("learned Vinewhip" in text for text in self.player.messages))

    def test_learning_failure_after_real_writes_rolls_back_everything(self):
        """An unexpected learner failure is not swallowed by the EXP wrapper."""
        from pokemon.utils import move_learning

        pokemon = self.learning_mon()
        self.give(1)
        before = self.snapshot(pokemon)
        original = move_learning.learn_move

        def fail_after_learning(*args, **kwargs):
            """Retain real move writes, then fail before committing the item use."""
            original(*args, **kwargs)
            raise RuntimeError("injected after learning")

        with patch.object(move_learning, "learn_move", fail_after_learning):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                self.command("Rare Candy=6")
        self.assertEqual(self.snapshot(pokemon), before)
        self.assertIsNone(self.player.ndb._evmenu)
        self.assertEqual(pokemon.level, before["pokemon"]["level"])
        self.assertFalse(any("learned" in text or "grew to level" in text for text in self.player.messages))

    def test_postcommit_ui_failure_does_not_misreport_a_rolled_back_use(self):
        """A failed prompt transport leaves the committed level/item truthful."""
        pokemon = self.learning_mon(full=True)
        self.give(1)
        with patch.object(FieldRareCandyUse, "_show_moves", side_effect=RuntimeError("UI unavailable")):
            with self.assertLogs("django.db.backends.base", level="ERROR"):
                self.command("Rare Candy=6")
        self.assertEqual(OwnedPokemon.objects.filter(pk=pokemon.pk).values_list("level", flat=True).get(), 3)
        self.assertEqual(self.trainer.get_item_quantity("Rare Candy"), 0)
        self.assertIn("grew to level 3", self.player.messages[-1])

    def test_full_moveset_prompt_opens_only_after_commit(self):
        """Keep the actual ordinary replacement menu outside rollbackable UI."""
        from django.db import transaction

        pokemon = self.learning_mon(full=True)
        self.give(1)
        with transaction.atomic():
            self.command("Rare Candy=6")
            self.assertIsNone(self.player.ndb._evmenu)
            self.assertTrue(pokemon.learned_moves.filter(name__iexact="Vinewhip").exists())
        self.assertIsNotNone(self.player.ndb._evmenu)
        self.assertEqual(self.trainer.get_item_quantity("Rare Candy"), 0)

    def test_outer_rollback_does_not_open_learning_prompt(self):
        """A rolled-back parent operation publishes no move UI or item effect."""
        from django.db import transaction

        pokemon = self.learning_mon(full=True)
        self.give(1)
        before = self.snapshot(pokemon)
        with self.assertRaisesRegex(RuntimeError, "outer rollback"):
            with transaction.atomic():
                self.command("Rare Candy=6")
                raise RuntimeError("outer rollback")
        self.assertEqual(self.snapshot(pokemon), before)
        self.assertIsNone(self.player.ndb._evmenu)
        self.assertEqual(pokemon.level, before["pokemon"]["level"])
        self.assertEqual(OwnedPokemon.objects.get(pk=pokemon.pk).level, before["pokemon"]["level"])
        self.assertFalse(any("grew to level" in text for text in self.player.messages))

    def race(self, *actions):
        """Use independent PostgreSQL connections, synchronized before input."""
        from django.db import close_old_connections

        barrier = Barrier(len(actions))

        def run(action):
            """Always close the worker connection after its command."""
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return action()
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            return list(pool.map(run, actions))

    def test_competing_commands_share_last_copy(self):
        """Two real +use commands cannot buy two level gains with one item."""
        self.give(1)
        self.race(lambda: self.command("Rare Candy=3"), lambda: self.command("Rare Candy=3"))
        row = self.snapshot()["pokemon"]
        self.assertEqual((row["level"], row["total_exp"]), (51, exp_for_level(51)))
        self.assertEqual(self.trainer.get_item_quantity("Rare Candy"), 0)
        self.assertEqual(sum("grew to level" in m for m in self.player.messages), 1)

    def test_competing_commands_with_two_copies_both_pay_and_grow(self):
        """Serialized legitimate uses observe fresh EXP and reach level 52."""
        self.give(2)
        self.race(lambda: self.command("Rare Candy=3"), lambda: self.command("Rare Candy=3"))
        row = self.snapshot()["pokemon"]
        self.assertEqual((row["level"], row["total_exp"]), (52, exp_for_level(52)))
        self.assertEqual(self.trainer.get_item_quantity("Rare Candy"), 0)


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
            from commands.player.cmd_party import CmdDepositPokemon
            from commands.player.cmd_sheet import CmdSheetPokemon
        from evennia.objects.models import ObjectDB
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon, get_max_hp
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot, MovesetSlot, PokemonLearnedMove
        from pokemon.models.stats import exp_for_level
        from pokemon.models.storage import PokemonPlacement, StorageBox, UserStorage
        from pokemon.models.trainer import Trainer
        from pokemon.services.field_items import FieldMedicineError
        from pokemon.services.field_progression import FieldRareCandyUse
        from pokemon.services.placement import PlacementService
        from pokemon.user import User
        COMMANDS = {"use": CmdUseItem, "inventory": CmdInventory, "party": CmdSheetPokemon, "deposit": CmdDepositPokemon}
        try:
            result = unittest.main(verbosity=2, exit=False).result
        finally:
            destination = os.environ.get("PF2_RARE_CANDY_EVIDENCE")
            if destination:
                Path(destination).write_text(json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())

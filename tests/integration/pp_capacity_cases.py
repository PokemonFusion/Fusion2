"""Prove ordinary PP-capacity commands with real disposable PostgreSQL rows."""

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


class PPPlayer(PlayerView):
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


class PPCapacityCases(unittest.TestCase):
    """Check targeting, capacity, raw bonus compatibility, rollback and contention."""

    def setUp(self):
        """Create a tagged ordinary owner with a genuinely gapped party."""
        self.character = ObjectDB.objects.create(db_key="pp-capacity-765-" + uuid4().hex, db_typeclass_path="pokemon.user.User")
        self.trainer, _ = Trainer.objects.get_or_create(user=self.character, defaults={"trainer_number": Trainer.objects.count() + 1})
        self.storage, _ = UserStorage.objects.get_or_create(user=self.character)
        StorageBox.objects.create(storage=self.storage, name="PP Box")
        self.player = PPPlayer(self.character, self.trainer, self.storage)
        self.player.pk = self.character.pk
        self.mon = self.create_mon()
        self.mon.activemoveslot_set.filter(slot=2).update(slot=3)

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
            "inventory": list(self.trainer.list_inventory().values("item_name", "quantity")),
            "learned": list(PokemonLearnedMove.objects.filter(pokemon_id=identifier).order_by("move_id").values()),
            "active": list(ActiveMoveslot.objects.filter(pokemon_id=identifier).order_by("slot").values()),
            "boosts": list(MovePPBoost.objects.filter(pokemon_id=identifier).order_by("move_id").values()),
            "sets": list(MovesetSlot.objects.filter(moveset__pokemon_id=identifier).order_by("pk").values()),
        }

    def give(self, amount=2, item="PP Up"):
        """Fixture setup grants bag stock separately from ordinary acceptance."""
        self.trainer.add_item(item, amount)

    def record(self, label, args, pokemon=None):
        """Retain ordinary input/output and independent SQL before/after proof."""
        before, start = self.snapshot(pokemon), len(self.player.messages)
        self.command(args)
        EVIDENCE.append({"label": label, "command": "+use " + args, "before": before,
                         "after": self.snapshot(pokemon), "messages": self.player.messages[start:]})


    def pp(self, slot=1):
        """Read current PP and authoritative maximum from independent SQL."""
        row = ActiveMoveslot.objects.filter(pokemon_id=self.mon.pk, slot=slot).select_related("move").get()
        return row.current_pp, OwnedPokemon.objects.get(pk=self.mon.pk).get_max_pp(row.move.name)

    def prompt(self, item="PP Up", target="3"):
        """Start the actual ordinary two-command player flow."""
        self.record("prompt-" + item, item + "=" + target)
        self.assertIn("Choose a move", self.player.messages[-1])
        self.assertIsInstance(self.player.ndb.pending_pp_item, dict)

    def test_discover_prompt_up_three_times_cap_and_reopen(self):
        """Inventory/party discovery reaches 42/49/56 with only three debits."""
        self.give(4)
        self.assertIn("PP Up", self.command("", "inventory"))
        self.assertIn(str(self.mon.pk), self.command("3", "party"))
        for capacity in (42, 49, 56):
            self.prompt()
            self.record("up-capacity-" + str(capacity), "1")
            self.assertEqual(self.pp(), (capacity, capacity))
            self.assertIsNone(self.player.ndb.pending_pp_item)
        self.prompt()
        before = self.snapshot()
        self.record("already-maxed", "Tackle")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.trainer.get_item_quantity("PP Up"), 1)
        self.assertEqual(self.character.db.inventory.get("Ppup"), 1)

    def test_max_fresh_and_partial_boosts(self):
        """Max fills the remaining capacity after zero, one or two Ups."""
        self.give(3, "PP Max")
        for bonus in (0, 7, 14):
            with self.subTest(bonus=bonus):
                MovePPBoost.objects.filter(pokemon=self.mon).delete()
                if bonus:
                    MovePPBoost.objects.create(pokemon=self.mon, move=self.mon.activemoveslot_set.get(slot=1).move, bonus_pp=bonus)
                self.mon.activemoveslot_set.filter(slot=1).update(current_pp=35 + bonus)
                self.prompt("PP Max")
                self.record("max-from-" + str(bonus), "Tackle")
                self.assertEqual(self.pp(), (56, 56))
        self.assertEqual(self.trainer.get_item_quantity("PP Max"), 0)

    def test_depleted_current_pp_increases_only_by_capacity_delta(self):
        """A capacity item preserves spent PP instead of acting as Max Ether."""
        self.give()
        self.mon.activemoveslot_set.filter(slot=1).update(current_pp=0)
        self.prompt()
        self.record("depleted-up", "1")
        self.assertEqual(self.pp(), (7, 42))
        self.give(1, "PP Max")
        self.prompt("PP Max")
        self.record("depleted-partial-max", "1")
        self.assertEqual(self.pp(), (21, 56))

    def test_unknown_current_pp_uses_existing_full_capacity_convention(self):
        """A NULL current PP slot follows the existing uninitialized-full rule."""
        self.give(1)
        self.mon.activemoveslot_set.filter(slot=1).update(current_pp=None)
        self.prompt()
        self.command("1")
        self.assertEqual(self.pp(), (42, 42))

    def test_gapped_displayed_slot_and_normalized_name(self):
        """Displayed slot 3 and spaced case variants select Water Gun exactly."""
        self.give()
        for selection, capacity in (("3", 30), ("WATER  GUN", 35)):
            self.prompt(target=str(self.mon.pk))
            self.record("gapped-or-named-move", selection)
            self.assertEqual(self.pp(3), (capacity, capacity))
            self.assertEqual(self.pp(), (35, 35))

    def test_nonexistent_compact_slot_and_unknown_selection_can_retry(self):
        """Slot 2 cannot silently choose displayed slot 3; invalid input pays none."""
        self.give(1)
        self.prompt()
        before = self.snapshot()
        for selection in ("2", "0", "4", "Water", "No Such Move", ""):
            self.record("invalid-move", selection)
            self.assertEqual(self.snapshot(), before)
            self.assertIn("Invalid", self.player.messages[-1])
        self.command("3")
        self.assertEqual(self.pp(3), (30, 30))

    def test_ambiguous_move_alias_rejected(self):
        """Legacy duplicate normalized spellings require investigation, not a guess."""
        duplicate = Move.objects.create(name="Water Gun")
        PokemonLearnedMove.objects.create(pokemon=self.mon, move=duplicate)
        ActiveMoveslot.objects.create(pokemon=self.mon, move=duplicate, slot=4, current_pp=25)
        self.give()
        self.prompt()
        before = self.snapshot()
        self.command("watergun")
        self.assertEqual(self.snapshot(), before)
        self.assertIn("ambiguous", self.player.messages[-1])
        # Even an exact slot cannot make two indistinguishable learned records
        # safe at the authoritative model boundary.
        self.command("3")
        self.assertEqual(self.snapshot(), before)

    def test_item_target_aliases_and_legacy_target_first(self):
        """Normal target spellings and compatible syntax keep canonical identity."""
        self.give(3)
        self.state(nickname="PP Buddy")
        for args in ("PPUp=PP Buddy", "3=PP Up", "PP Up=Mew"):
            self.record("target-spelling", args)
            self.command("Tackle")
        self.assertEqual(self.pp(), (56, 56))

    def test_ambiguous_pokemon_name_requires_canonical_slot(self):
        """Duplicate names do not choose a cached first match."""
        other = self.create_mon(slot=6)
        self.state(nickname="PP Buddy")
        self.state(other, nickname="PP Buddy")
        self.give(1)
        before = self.snapshot()
        self.record("ambiguous-pokemon", "PP Up=PP Buddy")
        self.assertEqual(self.snapshot(), before)
        self.assertIn("ambiguous", self.player.messages[-1])
        self.prompt(target="6")
        self.command("1")
        self.assertEqual(OwnedPokemon.objects.get(pk=other.pk).get_max_pp("Tackle"), 42)
        self.assertEqual(self.pp(), (35, 35))

    def test_fainted_target_and_unrelated_saved_state_preserved(self):
        """Capacity items neither heal/revive nor change other Pokemon state."""
        self.state(current_hp=0, status="slp", sleep_turns=2, friendship=203,
                   held_item="Everstone", flags=["ordinary-pp-test"])
        self.give(1)
        self.prompt()
        before = self.snapshot()
        self.record("fainted-target-state-preservation", "1")
        after = self.snapshot()
        for field in ("pokemon", "placement", "learned", "sets"):
            self.assertEqual(after[field], before[field])
        self.assertEqual(self.pp(), (42, 42))

    def test_postcommit_transport_failure_keeps_committed_effect_and_cache(self):
        """A disconnect after commit cannot report an unpaid or rolled-back boost."""
        self.give(2)
        self.prompt()
        with patch.object(self.player, "msg", side_effect=RuntimeError("transport unavailable")):
            with self.assertLogs("django.db.backends.base", level="ERROR"):
                self.command("1")
        self.assertEqual(self.pp(), (42, 42))
        self.assertEqual(self.trainer.get_item_quantity("PP Up"), 1)
        self.assertEqual(self.character.db.inventory.get("Ppup"), 1)
        self.assertIsNone(self.player.ndb.pending_pp_item)

    def test_initial_egg_box_and_foreign_targets_rejected(self):
        """Fresh eligibility rejects stored eggs, boxed UUIDs and foreign ownership."""
        self.give()
        self.state(is_egg=True)
        self.assertFalse(self.mon.is_egg)
        before = self.snapshot()
        self.command("PP Up=3")
        self.assertEqual(self.snapshot(), before)
        self.assertIsNone(self.player.ndb.pending_pp_item)
        self.state(is_egg=False)
        PlacementService(self.storage).to_box(self.mon)
        before = self.snapshot()
        self.command("PP Up=" + str(self.mon.pk))
        self.assertEqual(self.snapshot(), before)

    def test_normal_deposit_after_prompt_expires_target(self):
        """The audit's +box/deposit route cannot boost the now-boxed target."""
        self.give()
        self.prompt()
        self.assertIn("deposited", self.command(str(self.mon.pk), "deposit"))
        before = self.snapshot()
        self.record("prompt-then-normal-deposit", "1")
        self.assertEqual(self.snapshot(), before)
        self.assertIsNone(self.player.ndb.pending_pp_item)

    def test_release_after_prompt_rejected(self):
        """An actual placement release leaves no usable pending target."""
        self.give()
        self.prompt()
        PlacementService(self.storage).release(self.mon)
        before = self.snapshot()
        self.command("1")
        self.assertEqual(self.snapshot(), before)

    def test_changed_owner_after_prompt_rejected(self):
        """Fresh trainer identity beats stale caller/model ownership."""
        self.give()
        self.prompt()
        character = ObjectDB.objects.create(db_key="foreign-pp-" + uuid4().hex)
        trainer = Trainer.objects.create(user=character, trainer_number=Trainer.objects.count() + 1)
        self.state(trainer_id=trainer.pk)
        before = self.snapshot()
        self.command("1")
        self.assertEqual(self.snapshot(), before)

    def test_changed_egg_after_prompt_rejected(self):
        """A freshly stored egg flag prevents confirmation."""
        self.give()
        self.prompt()
        self.state(is_egg=True)
        before = self.snapshot()
        self.command("1")
        self.assertEqual(self.snapshot(), before)

    def test_party_replacement_never_retargets_pending_uuid(self):
        """Replacing party slot 3 cannot redirect its old prompt to a new Pokemon."""
        self.give()
        self.prompt()
        PlacementService(self.storage).to_box(self.mon)
        other = self.create_mon()
        before, other_before = self.snapshot(), self.snapshot(other)
        self.command("1")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.snapshot(other), other_before)

    def test_inactive_reservation_after_prompt_rejected(self):
        """A reserve that is not the player's current Fusion is ineligible."""
        self.give()
        self.prompt()
        PlacementService(self.storage).reserve_for_fusion(self.mon)
        before = self.snapshot()
        self.command("1")
        self.assertEqual(self.snapshot(), before)

    def test_current_fusion_aliases_and_changed_fusion(self):
        """Current Fusion accepts all normal aliases and loses eligibility on change."""
        PlacementService(self.storage).reserve_for_fusion(self.mon)
        self.character.db.fusion_id = str(self.mon.pk)
        self.give(4)
        for target in ("fusion", "self", "me"):
            self.prompt(target=target)
            self.command("1")
        self.assertEqual(self.pp(), (56, 56))
        self.prompt(target="fusion")
        self.character.db.fusion_id = None
        before = self.snapshot()
        self.command("1")
        self.assertEqual(self.snapshot(), before)

    def test_changed_active_move_identity_expires_prompt(self):
        """Changing the move behind a displayed number cannot redirect its item."""
        self.give()
        self.prompt()
        slot = self.mon.activemoveslot_set.get(slot=3)
        self.mon.activemoveslot_set.filter(slot=1).update(move=slot.move)
        before = self.snapshot()
        self.record("changed-move", "1")
        self.assertEqual(self.snapshot(), before)
        self.assertIn("stale", self.player.messages[-1])

    def test_changed_slot_or_bonus_expires_prompt(self):
        """Slot renumbering and another capacity change both require a fresh prompt."""
        self.give()
        self.prompt()
        self.mon.activemoveslot_set.filter(slot=3).update(slot=4)
        before = self.snapshot()
        self.command("1")
        self.assertEqual(self.snapshot(), before)
        self.prompt()
        self.assertTrue(self.mon.apply_pp_up("Tackle"))
        before = self.snapshot()
        self.command("1")
        self.assertEqual(self.snapshot(), before)

    def test_missing_stock_on_confirmation(self):
        """A prompt reserves no stock; confirmation checks the actual bag."""
        self.give(1)
        self.prompt()
        self.trainer.remove_item("PP Up")
        before = self.snapshot()
        self.record("stock-removed", "1")
        self.assertEqual(self.snapshot(), before)
        self.assertIsNone(self.player.ndb.pending_pp_item)

    def test_battle_guards_and_recheck_under_lock(self):
        """Both battle guards prevent confirmation effects."""
        self.give()
        self.prompt()
        before = self.snapshot()
        self.character.db.battle_lock = "fixture-battle"
        self.command("1")
        self.assertEqual(self.snapshot(), before)
        self.character.db.battle_lock = None
        self.player.ndb.battle_instance = object()
        self.command("1")
        self.assertEqual(self.snapshot(), before)
        self.player.ndb.battle_instance = None
        with patch("pokemon.services.field_items.require_no_battle_lock", return_value=False):
            self.command("1")
        self.assertEqual(self.snapshot(), before)

    def test_low_pp_and_unboostable_dex_policy(self):
        """Five-PP moves reach 6/7/8; all four noPPBoosts entries reject."""
        slot = self.mon.activemoveslot_set.get(slot=1)
        for name in ("Hyperbeam", "Sketch", "Revivalblessing", "Struggle", "Trumpcard"):
            move, _ = Move.objects.get_or_create(name=name)
            PokemonLearnedMove.objects.get_or_create(pokemon=self.mon, move=move)
            self.mon.activemoveslot_set.filter(pk=slot.pk).update(move=move, current_pp=5 if name in {"Hyperbeam", "Trumpcard"} else 1)
            if name == "Hyperbeam":
                self.give(3)
                for capacity in (6, 7, 8):
                    self.prompt()
                    self.command("1")
                    self.assertEqual(self.pp(), (capacity, capacity))
            else:
                for item in ("PP Up", "PP Max"):
                    self.give(1, item)
                    self.prompt(item)
                    before = self.snapshot()
                    self.record("unboostable-" + name, "1")
                    self.assertEqual(self.snapshot(), before)

    def test_legacy_raw_bonuses_preserved_and_bounded_recovery(self):
        """Never multiply saved raw PP; Max can finish a noncanonical in-range row."""
        move = self.mon.activemoveslot_set.get(slot=1).move
        for bonus in (1, 3, 6, 7, 14, 21, 22):
            MovePPBoost.objects.update_or_create(pokemon=self.mon, move=move, defaults={"bonus_pp": bonus})
            self.mon.activemoveslot_set.filter(slot=1).update(current_pp=35 + bonus)
            self.assertEqual(self.pp(), (35 + bonus, 35 + bonus))
            for item in ("PP Up", "PP Max"):
                # Reset before each probe so it audits precisely the saved row.
                MovePPBoost.objects.filter(pokemon=self.mon, move=move).update(bonus_pp=bonus)
                self.mon.activemoveslot_set.filter(slot=1).update(current_pp=35 + bonus)
                self.give(1, item)
                self.prompt(item)
                before = self.snapshot()
                self.record(f"legacy-{bonus}-{item}", "1")
                allowed = bonus < 21 and (item == "PP Max" or bonus in (7, 14))
                if allowed:
                    expected = 56 if item == "PP Max" else 35 + bonus + 7
                    self.assertEqual(self.pp(), (expected, expected))
                else:
                    self.assertEqual(self.snapshot(), before)

    def test_failed_debit_and_partial_debit_roll_back(self):
        """False returns before or after real debit cannot grant free capacity."""
        self.give()
        original = Trainer.remove_item

        def fail_after_debit(trainer, *args):
            """Fail after the actual inventory write to exercise outer rollback."""
            original(trainer, *args)
            return False

        for replacement in (lambda *args: False, fail_after_debit):
            self.prompt()
            before = self.snapshot()
            with patch.object(Trainer, "remove_item", replacement):
                self.record("failed-or-partial-debit", "1")
            self.assertEqual(self.snapshot(), before)
            self.assertEqual(self.character.db.inventory.get("Ppup"), 2)

    def test_failure_after_boost_save_rolls_back_all_rows(self):
        """A failure after real boost SQL rolls back bonus, PP and stock."""
        self.give()
        self.prompt()
        before = self.snapshot()
        original = MovePPBoost.save

        def fail_after_save(boost, *args, **kwargs):
            """Keep the real save, then inject a persistence failure."""
            original(boost, *args, **kwargs)
            raise RuntimeError("injected boost save failure")

        with patch.object(MovePPBoost, "save", fail_after_save):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                self.command("1")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.mon.get_max_pp("Tackle"), 35)
        self.assertIsNone(self.player.ndb.pending_pp_item)

    def test_failure_after_current_pp_save_rolls_back_all_rows(self):
        """Failure after bulk current-PP SQL also rolls back the prior bonus/debit."""
        from django.db.models.query import QuerySet

        self.give()
        self.prompt()
        before = self.snapshot()
        original = QuerySet.bulk_update

        def fail_after_save(queryset, *args, **kwargs):
            """Inject a fault only after actual active move writes."""
            result = original(queryset, *args, **kwargs)
            if queryset.model is ActiveMoveslot:
                raise RuntimeError("injected current PP save failure")
            return result

        with patch.object(QuerySet, "bulk_update", fail_after_save):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                self.command("1")
        self.assertEqual(self.snapshot(), before)

    def test_outer_rollback_keeps_caches_stock_and_notices_truthful(self):
        """Enclosing rollback publishes neither capacity, stock nor success."""
        from django.db import transaction

        self.give()
        self.prompt()
        before = self.snapshot()
        with self.assertRaisesRegex(RuntimeError, "outer rollback"):
            with transaction.atomic():
                self.command("1")
                raise RuntimeError("outer rollback")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.mon.get_max_pp("Tackle"), 35)
        self.assertEqual(self.character.db.inventory.get("Ppup"), 2)
        self.assertFalse(any("was increased" in text for text in self.player.messages))

    def test_outer_rollback_cannot_publish_prompt(self):
        """A rolled-back prompt start leaves no session state or UI."""
        from django.db import transaction

        self.give()
        with self.assertRaisesRegex(RuntimeError, "rollback"):
            with transaction.atomic():
                self.command("PP Up=3")
                raise RuntimeError("rollback")
        self.assertIsNone(self.player.ndb.pending_pp_item)
        self.assertFalse(any("Choose a move" in text for text in self.player.messages))

    def test_prompt_is_json_safe_and_consumed_prompt_cannot_replay(self):
        """Stable JSON identities replace cached models and prevent duplicate payment."""
        self.give()
        self.prompt()
        pending = self.player.ndb.pending_pp_item
        self.assertEqual(json.loads(json.dumps(pending)), pending)
        self.command("1")
        before = self.snapshot()
        with self.assertRaises(FieldMedicineError):
            FieldPPCapacityUse(self.player).confirm(pending, "1")
        self.command("1")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.trainer.get_item_quantity("PP Up"), 1)
        self.assertEqual(self.character.db.inventory.get("Ppup"), 1)

    def test_cancel_replacement_and_legacy_prompt_expiry(self):
        """Players can cancel or choose another item; old model prompts expire."""
        self.give()
        self.prompt()
        self.command("cancel")
        self.assertIsNone(self.player.ndb.pending_pp_item)
        self.prompt()
        old = self.player.ndb.pending_pp_item
        self.give(1, "PP Max")
        self.prompt("PP Max")
        with self.assertRaises(FieldMedicineError):
            FieldPPCapacityUse(self.player).confirm(old, "1")
        self.command("1")
        self.assertEqual(self.pp(), (56, 56))
        self.assertEqual(self.trainer.get_item_quantity("PP Up"), 2)
        self.player.ndb.pending_pp_item = {"pokemon": self.mon, "item": "ppup"}
        before = self.snapshot()
        self.command("1")
        self.assertEqual(self.snapshot(), before)

    def test_missing_learned_move_and_invalid_current_pp_rollback(self):
        """An inconsistent active/learned row or over-cap current PP spends none."""
        self.give()
        self.prompt()
        PokemonLearnedMove.objects.filter(pokemon=self.mon, move__name__iexact="Tackle").delete()
        before = self.snapshot()
        self.command("1")
        self.assertEqual(self.snapshot(), before)
        PokemonLearnedMove.objects.create(pokemon=self.mon, move=self.mon.activemoveslot_set.get(slot=1).move)
        self.mon.activemoveslot_set.filter(slot=1).update(current_pp=36)
        self.prompt()
        before = self.snapshot()
        self.command("1")
        self.assertEqual(self.snapshot(), before)

    def test_empty_moveset_missing_stock_and_bad_syntax(self):
        """Missing preconditions never create a paid effect or empty usable prompt."""
        before = self.snapshot()
        self.command("PP Up=3")
        self.assertEqual(self.snapshot(), before)
        self.give()
        for args in ("PP Up", "PP Up=", "PP Up=3/Tackle", "PP Up=Potion", "PP Up=1"):
            before = self.snapshot()
            self.command(args)
            self.assertEqual(self.snapshot(), before)
        self.mon.activemoveslot_set.all().delete()
        before = self.snapshot()
        self.command("PP Up=3")
        self.assertEqual(self.snapshot(), before)
        self.assertIsNone(self.player.ndb.pending_pp_item)

    def race(self, *actions):
        """Use independent connections synchronized immediately before commands."""
        from django.db import close_old_connections

        barrier = Barrier(len(actions))

        def run(action):
            """Keep per-thread connections isolated and always release them."""
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return action()
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            return list(pool.map(run, actions))

    def test_competing_final_copy_confirmations(self):
        """Two ordinary confirmations spend one final item and increase once."""
        self.give(1)
        self.prompt()
        self.race(lambda: self.command("1"), lambda: self.command("1"))
        self.assertEqual(self.pp(), (42, 42))
        self.assertEqual(self.trainer.get_item_quantity("PP Up"), 0)
        self.assertEqual(sum("was increased" in text for text in self.player.messages), 1)

    def test_two_copies_still_cannot_replay_one_prompt(self):
        """More stock cannot turn one prompt into two capacity purchases."""
        self.give(2)
        self.prompt()
        pending = self.player.ndb.pending_pp_item

        def confirm():
            """Capture the same prompt before either worker acquires its lock."""
            try:
                FieldPPCapacityUse(self.player).confirm(pending, "1")
                return True
            except FieldMedicineError:
                return False

        self.assertEqual(sorted(self.race(confirm, confirm)), [False, True])
        self.assertEqual(self.pp(), (42, 42))
        self.assertEqual(self.trainer.get_item_quantity("PP Up"), 1)
        self.assertEqual(self.character.db.inventory.get("Ppup"), 1)

    def test_direct_model_writers_share_capacity_lock(self):
        """Legacy model callbacks also serialize fresh bonus/current PP reads."""
        self.assertEqual(self.race(lambda: self.mon.apply_pp_up("Tackle"),
                                   lambda: self.mon.apply_pp_up("Tackle")), [True, True])
        self.assertEqual(self.pp(), (49, 49))


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
        from pokemon.models.moves import ActiveMoveslot, Move, MovePPBoost, MovesetSlot, PokemonLearnedMove
        from pokemon.models.stats import exp_for_level
        from pokemon.models.storage import PokemonPlacement, StorageBox, UserStorage
        from pokemon.models.trainer import Trainer
        from pokemon.services.field_items import FieldMedicineError
        from pokemon.services.field_pp import FieldPPCapacityUse
        from pokemon.services.placement import PlacementService
        from pokemon.user import User
        COMMANDS = {"use": CmdUseItem, "inventory": CmdInventory, "party": CmdSheetPokemon, "deposit": CmdDepositPokemon}
        try:
            result = unittest.main(verbosity=2, exit=False).result
        finally:
            destination = os.environ.get("PF2_PP_CAPACITY_EVIDENCE")
            if destination:
                Path(destination).write_text(json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())

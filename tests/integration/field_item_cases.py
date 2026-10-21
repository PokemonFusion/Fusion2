"""Run real +use medicine routes against a disposable PostgreSQL schema."""

import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres


class FieldItemCases(unittest.TestCase):
    """Verify command targeting, durable effects and failure boundaries."""

    def setUp(self):
        """Create ordinary owned Pokemon in a genuinely gapped party."""
        self.character = ObjectDB.objects.create(db_key="field-medicine-" + uuid4().hex)
        self.trainer = Trainer.objects.create(
            user=self.character, trainer_number=Trainer.objects.count() + 1
        )
        self.storage = UserStorage.objects.create(user=self.character)
        self.owned = self.create_mon(slot=3)
        self.maximum = get_max_hp(self.owned)
        self.messages = []
        self.caller = SimpleNamespace(
            pk=self.character.pk, trainer=self.trainer, storage=self.storage,
            db=self.character.db, ndb=SimpleNamespace(pending_pp_item=None),
            msg=self.messages.append,
            get_active_pokemon_by_slot=lambda slot: self.storage.get_party_slots()[slot - 1]
            if slot in range(1, 7) else None,
        )

    def create_mon(self, *, slot=6, species="Mew"):
        """Place a fresh production Pokemon in an explicit canonical slot."""
        mon = create_owned_pokemon(
            species, self.trainer, 50, nature="Hardy", ivs=[0] * 6, evs=[0] * 6,
            active_move_names=["Tackle", "Watergun"],
        )
        PlacementService(self.storage).to_party(mon, slot=slot)
        return mon

    def state(self, mon=None, **fields):
        """Write fixture state without trusting or refreshing the identity map."""
        OwnedPokemon.objects.filter(pk=(mon or self.owned).pk).update(**fields)

    def row(self, mon=None):
        """Read authoritative rows rather than Evennia's shared Python instance."""
        return OwnedPokemon.objects.filter(pk=(mon or self.owned).pk).values().get()

    def command(self, args, caller=None):
        """Invoke the shipped +use command, with no effect callback substitution."""
        command = CmdUseItem()
        command.caller, command.args = caller or self.caller, args
        command.parse()
        command.func()

    def give(self, item, quantity=2):
        """Provide inventory through the real inventory transaction boundary."""
        self.trainer.add_item(item, quantity)

    def test_hp_medicine_routes_and_caps(self):
        """Every existing HP restorative persists and consumes exactly once."""
        for item, amount in [
            ("Potion", 20), ("Super Potion", 60), ("Hyper Potion", 120),
            ("Max Potion", self.maximum), ("Energy Powder", 60), ("Energy Root", 120),
        ]:
            with self.subTest(item=item):
                self.state(current_hp=1, status="", friendship=70)
                self.give(item)
                self.command(f"{item}=3")
                row = self.row()
                self.assertEqual(row["current_hp"], min(self.maximum, amount + 1))
                self.assertEqual(self.trainer.get_item_quantity(item), 1)
                self.assertIn("Used " + item, self.messages[-1])
                expected = {"Energy Powder": 65, "Energy Root": 60}.get(item, 70)
                self.assertEqual(row["friendship"], expected)

    def test_status_routes_clear_persisted_sleep_and_leave_hp(self):
        """Specific cures, Full Heal and Heal Powder use durable status codes."""
        for item, statuses in [
            ("Antidote", ["psn", "tox"]), ("Paralyze Heal", ["par"]),
            ("Burn Heal", ["brn"]), ("Ice Heal", ["frz"]), ("Awakening", ["slp"]),
            ("Full Heal", ["brn", "psn", "tox", "frz", "slp", "par"]),
            ("Heal Powder", ["brn", "psn", "tox", "frz", "slp", "par"]),
        ]:
            for status in statuses:
                with self.subTest(item=item, status=status):
                    self.state(current_hp=12, status=status, sleep_turns=2, friendship=200)
                    before = self.trainer.get_item_quantity(item)
                    self.give(item, 1)
                    self.command(f"{item}=3")
                    row = self.row()
                    self.assertEqual((row["current_hp"], row["status"], row["sleep_turns"]), (12, "", None))
                    self.assertEqual(row["friendship"], 190 if item == "Heal Powder" else 200)
                    self.assertEqual(self.trainer.get_item_quantity(item), before)

    def test_full_restore_hp_only_status_only_and_both(self):
        """Full Restore consumes once when either or both parts apply."""
        for hp, status in [(1, "brn"), (1, ""), (self.maximum, "slp")]:
            with self.subTest(hp=hp, status=status):
                self.state(current_hp=hp, status=status, sleep_turns=2)
                self.give("Full Restore", 1)
                self.command("Full Restore=3")
                row = self.row()
                self.assertEqual((row["current_hp"], row["status"], row["sleep_turns"]), (self.maximum, "", None))
                self.assertEqual(self.trainer.get_item_quantity("Full Restore"), 0)

    def test_revive_reserve_and_repeated_no_effect(self):
        """Revive slot 6 while slot 3 stays untouched; retries become free no-ops."""
        reserve = self.create_mon(species="Eevee")
        maximum = get_max_hp(reserve)
        before = self.row()
        for item, hp in [("Revive", maximum // 2), ("Max Revive", maximum), ("Revival Herb", maximum)]:
            with self.subTest(item=item):
                self.state(reserve, current_hp=0, friendship=200)
                self.give(item)
                self.command(f"{item}=6")
                self.assertEqual(self.row(reserve)["current_hp"], hp)
                self.command(f"{item}=6")
                self.assertIn("No item was consumed", self.messages[-1])
                self.assertEqual(self.trainer.get_item_quantity(item), 1)
                self.assertEqual(self.row(reserve)["friendship"], 180 if item == "Revival Herb" else 200)
        self.assertEqual(self.row(), before)

    def pp_setup(self):
        """Retain a gap in active moves and a boosted authoritative PP cap."""
        slots = list(self.owned.activemoveslot_set.order_by("slot"))
        slots[1].slot = 4
        slots[1].save(update_fields=["slot"])
        MovePPBoost.objects.create(pokemon=self.owned, move=slots[1].move, bonus_pp=15)
        self.owned.activemoveslot_set.update(current_pp=0)
        return slots

    def pp(self):
        """Read the current PP values in real slot order."""
        return list(self.owned.activemoveslot_set.order_by("slot").values_list("current_pp", flat=True))

    def test_all_pp_items_selected_names_and_real_slots(self):
        """Ether family uses exact selected move identity; elixirs restore all."""
        self.pp_setup()
        for item, suffix, expected in [
            ("Ether", "/Water Gun", [0, 10]), ("Max Ether", "/4", [0, 40]),
            ("Elixir", "", [10, 10]), ("Max Elixir", "", [35, 40]),
        ]:
            with self.subTest(item=item):
                self.owned.activemoveslot_set.update(current_pp=0)
                self.give(item)
                self.command(f"{item}=3{suffix}")
                self.assertEqual(self.pp(), expected)
                self.assertEqual(self.trainer.get_item_quantity(item), 1)
        self.owned.activemoveslot_set.update(current_pp=0)
        self.give("Ether", 1)
        self.command("Ether=3")
        self.assertEqual(self.pp(), [10, 0])

    def test_pp_caps_full_pp_unknown_move_and_fainted_guards(self):
        """No matching depleted move and fainted targets never cost an item."""
        slots = self.pp_setup()
        ActiveMoveslot.objects.filter(pk=slots[0].pk).update(current_pp=34)
        ActiveMoveslot.objects.filter(pk=slots[1].pk).update(current_pp=40)
        self.give("Ether", 5)
        self.command("Ether=3/1")
        self.assertEqual(self.pp(), [35, 40])
        for args in ["Ether=3/1", "Ether=3/2", "Ether=3/Thunder", "Ether=3"]:
            self.command(args)
            self.assertIn("No item was consumed", self.messages[-1])
        self.state(current_hp=0)
        self.owned.activemoveslot_set.update(current_pp=0)
        self.command("Ether=3/4")
        self.assertEqual(self.pp(), [0, 0])
        self.assertEqual(self.trainer.get_item_quantity("Ether"), 4)

    def test_herb_high_low_friendship_floor_and_free_no_effect(self):
        """All four herbs apply only their documented friendship penalty."""
        for item, low, high, status, hp in [
            ("Energy Powder", 5, 10, "", 1), ("Energy Root", 10, 15, "", 1),
            ("Heal Powder", 5, 10, "par", self.maximum),
            ("Revival Herb", 15, 20, "", 0),
        ]:
            for friendship, penalty in [(70, low), (200, high), (1, low)]:
                with self.subTest(item=item, friendship=friendship):
                    self.state(current_hp=hp, status=status, friendship=friendship)
                    self.give(item, 1)
                    self.command(f"{item}=3")
                    self.assertEqual(self.row()["friendship"], max(0, friendship - penalty))
            self.state(current_hp=self.maximum, status="", friendship=70)
            self.give(item, 1)
            self.command(f"{item}=3")
            self.assertEqual(self.row()["friendship"], 70)
            self.assertIn("No item was consumed", self.messages[-1])

    def test_wrong_state_and_missing_inventory_are_free(self):
        """Healthy HP, wrong cures and fainted healing cannot consume medicine."""
        for item, hp, status in [
            ("Potion", self.maximum, ""), ("Potion", 0, ""),
            ("Antidote", 12, "brn"), ("Full Heal", 0, "psn"),
            ("Full Restore", 0, "brn"), ("Revive", 12, ""),
        ]:
            with self.subTest(item=item, hp=hp, status=status):
                self.state(current_hp=hp, status=status)
                before = self.trainer.get_item_quantity(item)
                self.give(item, 1)
                self.command(f"{item}=3")
                self.assertEqual(self.trainer.get_item_quantity(item), before + 1)
                self.assertEqual((self.row()["current_hp"], self.row()["status"]), (hp, status))
        self.state(current_hp=1)
        self.command("Super Potion=3")
        self.assertIn("don't have", self.messages[-1])
        self.assertEqual(self.row()["current_hp"], 1)

    def test_slot_name_id_and_legacy_syntax_resolve_same_target(self):
        """Aliases and a gap never turn canonical slot 3 into compact slot 1."""
        self.give("Super Potion", 5)
        for args in ["super-potion=3", "Mew=Super Potion", f"Super Potion={self.owned.pk}"]:
            self.state(current_hp=1)
            self.command(args)
            self.assertEqual(self.row()["current_hp"], 61)
        self.state(current_hp=1)
        self.command("Super Potion=1")
        self.assertEqual(self.row()["current_hp"], 1)
        self.assertEqual(self.trainer.get_item_quantity("Super Potion"), 2)

    def test_ambiguous_name_and_foreign_id_are_rejected(self):
        """Duplicate species need slots; a foreign UUID never exposes a target."""
        reserve = self.create_mon()
        self.state(current_hp=1)
        self.state(reserve, current_hp=1)
        self.give("Potion")
        self.command("Potion=Mew")
        self.assertIn("ambiguous", self.messages[-1])
        other = ObjectDB.objects.create(db_key="foreign-" + uuid4().hex)
        trainer = Trainer.objects.create(user=other, trainer_number=Trainer.objects.count() + 1)
        foreign = create_owned_pokemon("Eevee", trainer, 5)
        self.command(f"Potion={foreign.pk}")
        self.assertEqual(self.trainer.get_item_quantity("Potion"), 2)
        self.assertEqual(self.row()["current_hp"], 1)

    def test_egg_box_and_inactive_fusion_are_rejected(self):
        """Only a usable canonical party member or the actual Fusion qualifies."""
        self.state(current_hp=1, is_egg=True)
        self.give("Potion", 3)
        self.command("Potion=3")
        self.assertIn("eggs", self.messages[-1])
        self.state(is_egg=False)
        PlacementService(self.storage).to_box(self.owned)
        self.command(f"Potion={self.owned.pk}")
        PlacementService(self.storage).to_party(self.owned, slot=3)
        PlacementService(self.storage).reserve_for_fusion(self.owned)
        self.command(f"Potion={self.owned.pk}")
        self.command("Potion=fusion")
        self.assertEqual(self.trainer.get_item_quantity("Potion"), 3)
        self.assertEqual(self.row()["current_hp"], 1)

    def test_current_fusion_and_self_alias_can_receive_medicine(self):
        """The reserved Pokemon of this character's actual Fusion is eligible."""
        PlacementService(self.storage).reserve_for_fusion(self.owned)
        self.character.db.fusion_id = str(self.owned.pk)
        self.give("Potion")
        self.state(current_hp=1)
        self.command("Potion=fusion")
        self.assertEqual(self.row()["current_hp"], 21)
        self.command("Potion=self")
        self.assertEqual(self.row()["current_hp"], 41)
        self.assertEqual(self.trainer.get_item_quantity("Potion"), 0)

    def test_fresh_database_values_override_stale_cached_target(self):
        """Repeat use sees persisted HP and ownership, not an old model snapshot."""
        self.owned.current_hp = 1
        self.state(current_hp=self.maximum)
        self.give("Potion")
        self.command("Potion=3")
        self.assertEqual(self.trainer.get_item_quantity("Potion"), 2)
        self.assertEqual(self.owned.current_hp, self.maximum)
        self.state(current_hp=1)
        self.command("Potion=3")
        self.assertEqual(self.row()["current_hp"], 21)

    def test_moved_target_and_battle_guards_rechecked_inside_service(self):
        """A stale client selection cannot bypass current placement or context."""
        self.state(current_hp=1)
        self.give("Potion", 3)
        service = FieldMedicineUse(self.caller)
        PlacementService(self.storage).to_box(self.owned)
        with self.assertRaises(FieldMedicineError):
            service.use("Potion", "3")
        PlacementService(self.storage).to_party(self.owned, slot=3)
        self.character.db.battle_lock = "active-test-battle"
        self.command("Potion=3")
        self.assertIsNone(service.use("Potion", "3"))
        self.character.db.battle_lock = None
        self.caller.ndb.battle_instance = object()
        self.command("Potion=3")
        self.assertIsNone(service.use("Potion", "3"))
        self.assertEqual(self.row()["current_hp"], 1)
        self.assertEqual(self.trainer.get_item_quantity("Potion"), 3)

    def test_invalid_syntax_and_move_selectors_do_not_consume(self):
        """Malformed commands and selectors on all-move items stay safe."""
        self.state(current_hp=1)
        self.give("Potion")
        self.give("Elixir")
        for args in ["Potion", "Potion=", "Potion=/Tackle", "Potion=3/", "Potion=3/Tackle", "Elixir=3/1", "Potion=Rare Candy"]:
            self.command(args)
        self.assertEqual(self.row()["current_hp"], 1)
        self.assertEqual(self.trainer.get_item_quantity("Potion"), 2)
        self.assertEqual(self.trainer.get_item_quantity("Elixir"), 2)

    def test_hp_save_failure_rolls_back_item_and_shared_instance(self):
        """A failed durable write cannot leave a debit or stale healed cache."""
        self.state(current_hp=1, friendship=200)
        self.give("Energy Root")
        original = OwnedPokemon.save

        def fail_save(mon, *args, **kwargs):
            """Inject a failure after the real effect write, inside its transaction."""
            original(mon, *args, **kwargs)
            if mon.pk == self.owned.pk and "current_hp" in kwargs.get("update_fields", []):
                raise RuntimeError("injected field medicine save failure")

        with patch.object(OwnedPokemon, "save", fail_save):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                self.command("Energy Root=3")
        self.assertEqual(self.row()["current_hp"], 1)
        self.assertEqual(self.row()["friendship"], 200)
        self.assertEqual(self.owned.current_hp, 1)
        self.assertEqual(self.trainer.get_item_quantity("Energy Root"), 2)

    def test_failed_inventory_debit_applies_no_hp_status_pp_or_herb_effect(self):
        """A rejected debit cannot apply any part of a field medicine effect."""
        self.pp_setup()
        self.state(current_hp=1, status="brn", friendship=200)
        for item in ["Full Restore", "Energy Root", "Max Elixir"]:
            with self.subTest(item=item):
                self.give(item)
                with patch.object(Trainer, "remove_item", return_value=False):
                    self.command(f"{item}=3")
                row = self.row()
                self.assertEqual((row["current_hp"], row["status"], row["friendship"]), (1, "brn", 200))
                self.assertEqual(self.pp(), [0, 0])
                self.assertEqual(self.trainer.get_item_quantity(item), 2)

    def test_changed_owner_cannot_use_stale_party_membership(self):
        """A stale placement or cached trainer never permits a foreign heal."""
        other = ObjectDB.objects.create(db_key="new-owner-" + uuid4().hex)
        trainer = Trainer.objects.create(user=other, trainer_number=Trainer.objects.count() + 1)
        self.give("Potion")
        self.state(current_hp=1, trainer_id=trainer.pk)
        self.command("Potion=3")
        self.assertEqual(self.row()["current_hp"], 1)
        self.assertEqual(self.trainer.get_item_quantity("Potion"), 2)

    def test_existing_pp_capacity_prompts_and_rare_candy_remain_usable(self):
        """The legacy field items still work; restoratives honor their real boosts."""
        # Preserve PF2's existing +1/+3 capacity progression; this issue wires
        # restoratives to the stored boost rather than changing that policy.
        for item, maximum in [("PP Up", 36), ("PP Max", 39)]:
            self.give(item, 1)
            self.command(f"{item}=3")
            self.assertIn("Choose a move", self.messages[-1])
            self.command("Tackle")
            self.assertEqual(self.trainer.get_item_quantity(item), 0)
            self.assertEqual(self.owned.get_max_pp("Tackle"), maximum)
            self.owned.activemoveslot_set.update(current_pp=0)
            self.give("Max Ether", 1)
            self.command("Max Ether=3/Tackle")
            self.assertEqual(self.pp()[0], maximum)
        self.give("Rare Candy", 1)
        self.command("Rare Candy=3")
        self.assertEqual(self.row()["level"], 51)
        self.assertEqual(self.trainer.get_item_quantity("Rare Candy"), 0)

    def test_ordinary_player_command_walkthrough_and_battle_rebuild(self):
        """Record concrete +use output and SQL results, then rebuild battle state."""
        reserve = self.create_mon(species="Eevee")
        self.pp_setup()
        self.state(current_hp=1, status="psn")
        self.state(reserve, current_hp=0)
        steps = []
        for item, args, mon in [
            ("Potion", "Potion=3", self.owned),
            ("Antidote", "Antidote=3", self.owned),
            ("Revive", "Revive=6", reserve),
            ("Max Ether", "Max Ether=3/Water Gun", self.owned),
            ("Elixir", "Elixir=3", self.owned),
            ("Energy Root", "Energy Root=3", self.owned),
        ]:
            self.give(item, 1)
            before = self.row(mon)
            self.command(args)
            after = self.row(mon)
            self.assertTrue(self.messages[-1].startswith("Used "), self.messages[-1])
            self.assertEqual(self.trainer.get_item_quantity(item), 0)
            steps.append({"command": "+use " + args, "output": self.messages[-1],
                          "before": {k: before[k] for k in ("current_hp", "status", "friendship")},
                          "after": {k: after[k] for k in ("current_hp", "status", "friendship")},
                          "party_3_pp": self.pp(), "remaining_item": 0})
        restored = Pokemon.from_dict(build_battle_pokemon_from_model(self.owned).to_dict())
        row = self.row()
        self.assertEqual((restored.hp, restored.status or ""), (row["current_hp"], row["status"]))
        self.assertEqual([move.pp for move in restored.moves], self.pp())
        print("FIELD_COMMAND_WALKTHROUGH " + json.dumps(steps))

    def test_later_pp_write_failure_rolls_back_all_moves_and_debit(self):
        """An all-move restore is one transaction even if its last save fails."""
        slots = self.pp_setup()
        self.give("Max Elixir")
        original = ActiveMoveslot.save

        def fail_second(slot, *args, **kwargs):
            """Fail after the second write to prove rollback of the first too."""
            original(slot, *args, **kwargs)
            if slot.pk == slots[1].pk:
                raise RuntimeError("injected second PP write failure")

        with patch.object(ActiveMoveslot, "save", fail_second):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                self.command("Max Elixir=3")
        self.assertEqual(self.pp(), [0, 0])
        self.assertEqual(self.trainer.get_item_quantity("Max Elixir"), 2)

    def race(self, *actions):
        """Run callers on independent connections, meeting just before use."""
        from django.db import close_old_connections

        barrier = Barrier(len(actions))

        def run(action):
            """Close thread connections even if a transaction fails."""
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return action()
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            return list(pool.map(run, actions))

    def test_competing_commands_cannot_spend_the_last_item_twice(self):
        """Two simultaneous +use commands share one inventory and target lock."""
        self.state(current_hp=1)
        self.give("Potion", 1)
        self.race(lambda: self.command("Potion=3"), lambda: self.command("Potion=3"))
        self.assertEqual(self.row()["current_hp"], 21)
        self.assertEqual(self.trainer.get_item_quantity("Potion"), 0)
        self.assertEqual(sum(message.startswith("Used Potion") for message in self.messages), 1)

    def test_competing_full_heals_debit_only_the_effective_use(self):
        """A waiting command rechecks fresh state after another one heals it."""
        self.state(current_hp=1)
        self.give("Max Potion", 2)
        self.race(lambda: self.command("Max Potion=3"), lambda: self.command("Max Potion=3"))
        self.assertEqual(self.row()["current_hp"], self.maximum)
        self.assertEqual(self.trainer.get_item_quantity("Max Potion"), 1)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from evennia.commands.command import Command

        with patch.object(evennia, "Command", Command):
            from commands.player.cmd_inventory import CmdUseItem
        from evennia.objects.models import ObjectDB

        from pokemon.battle.battledata import Pokemon
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon, get_max_hp
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot, MovePPBoost
        from pokemon.models.storage import UserStorage
        from pokemon.models.trainer import Trainer
        from pokemon.services.field_items import FieldMedicineError, FieldMedicineUse
        from pokemon.services.placement import PlacementService
        from utils.pokemon_utils import build_battle_pokemon_from_model

        unittest.main(verbosity=2)

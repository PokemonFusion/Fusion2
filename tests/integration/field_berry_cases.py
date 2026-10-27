"""Exercise ordinary berry +use routes with real models in disposable PostgreSQL."""

import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres


class FieldBerryCases(unittest.TestCase):
    """Check exact saved effects, the feeding allowlist and transaction failures."""

    def setUp(self):
        """Create an ordinary owner and a party member in canonical slot 3."""
        self.character = ObjectDB.objects.create(db_key="berry-field-" + uuid4().hex)
        self.trainer = Trainer.objects.create(user=self.character, trainer_number=Trainer.objects.count() + 1)
        self.storage = UserStorage.objects.create(user=self.character)
        self.mon = self.create_mon(slot=3)
        self.maximum = get_max_hp(self.mon)
        self.messages = []
        self.caller = SimpleNamespace(
            character=self.character,
            pk=self.character.pk, trainer=self.trainer, storage=self.storage,
            db=self.character.db, ndb=SimpleNamespace(pending_pp_item=None), msg=self.messages.append,
            get_active_pokemon_by_slot=lambda slot: self.storage.get_party_slots()[slot - 1]
            if slot in range(1, 7) else None,
        )

    def create_mon(self, slot=6):
        """Create moves and placement with the production factory."""
        mon = create_owned_pokemon(
            "Mew", self.trainer, 50, nature="Hardy", ivs=[0] * 6, evs=[0] * 6,
            active_move_names=["Tackle", "Watergun"],
        )
        PlacementService(self.storage).to_party(mon, slot=slot)
        return mon

    def state(self, mon=None, **fields):
        """Write authoritative fixture fields while deliberately leaving stale caches."""
        OwnedPokemon.objects.filter(pk=(mon or self.mon).pk).update(**fields)

    def row(self, mon=None):
        """Bypass Evennia's identity map for effect assertions."""
        return OwnedPokemon.objects.filter(pk=(mon or self.mon).pk).values().get()

    def command(self, args):
        """Call the shipped command parser/function, without substituting effects."""
        command = CmdUseItem()
        command.caller, command.args = self.caller, args
        command.parse()
        command.func()

    def give(self, name, amount=1):
        """Add inventory through its real serialized transaction."""
        self.trainer.add_item(name, amount)

    def fresh(self):
        """Refresh scalar fields directly from SQL before helper calculations."""
        FieldMedicineUse._refresh(self.mon, self.row())
        return self.mon

    def test_all_recovery_berries_and_juice_heal_without_consuming_held_item(self):
        """Fixed/fractional healing works above held trigger thresholds and caps."""
        for item, amount in [
            ("Oran Berry", 10), ("Berry Juice", 20), ("Sitrus Berry", self.maximum // 4),
            *[(name + " Berry", self.maximum // 3) for name in ("Figy", "Wiki", "Mago", "Aguav", "Iapapa")],
        ]:
            with self.subTest(item=item):
                self.state(current_hp=self.maximum - 1, held_item="Leftovers", nature="Hardy")
                self.give(item, 2)
                self.command(f"{item}=3")
                self.assertEqual(self.row()["current_hp"], self.maximum)
                self.assertEqual(self.row()["held_item"], "Leftovers")
                self.command(f"{item}=3")
                self.assertIn("No item was consumed", self.messages[-1])
                self.assertEqual(self.trainer.get_item_quantity(item), 1)
                self.state(current_hp=1)
                self.command(f"{item}=3")
                self.assertEqual(self.row()["current_hp"], 1 + amount)
                self.assertEqual(self.trainer.get_item_quantity(item), 0)

    def test_flavor_recovery_is_field_hp_only(self):
        """A disliked flavor's combat confusion is not a saved field condition."""
        self.state(current_hp=1, nature="Bold", status="psn", friendship=70, held_item="Figy Berry")
        self.give("Figy Berry")
        self.command("Figy Berry=3")
        row = self.row()
        self.assertEqual((row["current_hp"], row["status"], row["friendship"]), (1 + self.maximum // 3, "psn", 70))
        self.assertEqual(row["held_item"], "Figy Berry")

    def test_all_specific_status_berries_and_lum_cure_saved_conditions(self):
        """Specific cures and every Lum major status persist and clear sleep."""
        for item, statuses in [
            ("Cheri Berry", ["par"]), ("Chesto Berry", ["slp"]),
            ("Pecha Berry", ["psn", "tox"]), ("Rawst Berry", ["brn"]), ("Aspear Berry", ["frz"]),
            ("Lum Berry", ["par", "slp", "psn", "tox", "brn", "frz"]),
        ]:
            for status in statuses:
                with self.subTest(item=item, status=status):
                    self.state(current_hp=12, status=status, sleep_turns=2, friendship=70)
                    self.give(item)
                    self.command(f"{item}=3")
                    row = self.row()
                    self.assertEqual((row["current_hp"], row["status"], row["sleep_turns"], row["friendship"]), (12, "", None, 70))
                    self.assertEqual(self.trainer.get_item_quantity(item), 0)

    def test_no_effect_wrong_status_and_fainted_recovery_are_free(self):
        """Field berries cannot revive or cure the wrong saved condition."""
        for item, hp, status in [
            ("Oran Berry", 0, ""), ("Sitrus Berry", self.maximum, ""),
            ("Berry Juice", 0, ""), ("Figy Berry", 0, ""),
            ("Cheri Berry", 12, "brn"), ("Lum Berry", 12, ""), ("Lum Berry", 0, "psn"),
        ]:
            with self.subTest(item=item, hp=hp):
                self.state(current_hp=hp, status=status)
                before = self.trainer.get_item_quantity(item)
                self.give(item)
                self.command(f"{item}=3")
                self.assertIn("No item was consumed", self.messages[-1])
                self.assertEqual(self.trainer.get_item_quantity(item), before + 1)
                self.assertEqual((self.row()["current_hp"], self.row()["status"]), (hp, status))

    def pp_setup(self):
        """Use real move slots 1/4 with the latter's stored PP boost."""
        slots = list(self.mon.activemoveslot_set.order_by("slot"))
        slots[1].slot = 4
        slots[1].save(update_fields=["slot"])
        MovePPBoost.objects.create(pokemon=self.mon, move=slots[1].move, bonus_pp=15)
        self.mon.activemoveslot_set.update(current_pp=0)
        return slots

    def pp(self):
        """Read PP directly in canonical move-slot order."""
        return list(self.mon.activemoveslot_set.order_by("slot").values_list("current_pp", flat=True))

    def test_leppa_selected_name_real_slot_and_first_depleted(self):
        """Leppa shares single-move PP semantics, including boosted caps."""
        slots = self.pp_setup()
        self.give("Leppa Berry", 6)
        self.command("Leppa Berry=3/Water Gun")
        self.assertEqual(self.pp(), [0, 10])
        ActiveMoveslot.objects.filter(pk=slots[1].pk).update(current_pp=39)
        self.command("Leppa Berry=3/4")
        self.assertEqual(self.pp(), [0, 40])
        for args in ["Leppa Berry=3/4", "Leppa Berry=3/2", "Leppa Berry=3/Unknown"]:
            self.command(args)
            self.assertIn("No item was consumed", self.messages[-1])
        self.command("Leppa Berry=3")
        self.assertEqual(self.pp(), [10, 40])
        self.state(current_hp=0)
        self.command("Leppa Berry=3/1")
        self.assertEqual(self.pp(), [10, 40])
        self.assertEqual(self.trainer.get_item_quantity("Leppa Berry"), 3)

    def test_each_ev_berry_reduces_only_its_stat_and_recalculates(self):
        """All six EV mappings persist, retain array shape and change real stats."""
        names = ["Pomeg", "Kelpsy", "Qualot", "Hondew", "Grepa", "Tamato"]
        stats = ["hp", "attack", "defense", "special_attack", "special_defense", "speed"]
        for index, name in enumerate(names):
            with self.subTest(berry=name):
                initial = [0] * 6
                initial[index] = 252
                self.state(evs=initial, friendship=70, held_item="Leftovers")
                before_stats = get_stats(self.fresh())
                self.state(current_hp=before_stats["hp"])
                self.give(name + " Berry")
                self.command(f"{name} Berry=3")
                row = self.row()
                expected = initial.copy()
                expected[index] -= 10
                self.assertEqual(row["evs"], expected)
                self.assertEqual(row["friendship"], 80)
                after_stats = get_stats(self.fresh())
                self.assertLess(after_stats[stats[index]], before_stats[stats[index]])
                self.assertEqual(row["current_hp"], after_stats["hp"])
                self.assertEqual(row["held_item"], "Leftovers")
                self.assertEqual(self.trainer.get_item_quantity(name + " Berry"), 0)

    def test_each_ev_floor_friendship_only_ev_only_and_terminal_no_effect(self):
        """Each berry removes min(10, EV), raises friendship independently, then stops."""
        for item, index in [(name + " Berry", i) for i, name in enumerate(
            ["Pomeg", "Kelpsy", "Qualot", "Hondew", "Grepa", "Tamato"]
        )]:
            for value in [0, 1, 9, 10, 11]:
                with self.subTest(item=item, ev=value):
                    evs = [0] * 6
                    evs[index] = value
                    self.state(evs=evs, friendship=255, current_hp=1)
                    before = self.trainer.get_item_quantity(item)
                    self.give(item)
                    self.command(f"{item}=3")
                    self.assertEqual(self.row()["evs"][index], max(0, value - 10))
                    self.assertEqual(self.row()["friendship"], 255)
                    self.assertEqual(self.trainer.get_item_quantity(item), before + (value == 0))
            self.state(evs=[0] * 6, friendship=70)
            self.give(item)
            before = self.trainer.get_item_quantity(item)
            self.command(f"{item}=3")
            self.assertEqual(self.row()["friendship"], 80)
            self.assertEqual(self.row()["evs"], [0] * 6)
            self.assertEqual(self.trainer.get_item_quantity(item), before - 1)

    def test_friendship_tiers_thresholds_and_cap(self):
        """The documented PF2 +10/+5/+2 policy clamps friendship to 255."""
        for current, expected in [(0, 10), (99, 109), (100, 105), (199, 204), (200, 202), (254, 255), (255, 255)]:
            with self.subTest(friendship=current):
                self.state(evs=[0] * 6, friendship=current)
                self.give("Kelpsy Berry")
                before = self.trainer.get_item_quantity("Kelpsy Berry")
                self.command("Kelpsy Berry=3")
                self.assertEqual(self.row()["friendship"], expected)
                self.assertEqual(self.trainer.get_item_quantity("Kelpsy Berry"), before - (current < 255))

    def test_pomeg_preserves_missing_hp_clamps_living_and_never_revives(self):
        """HP EV loss updates max HP with helpers while avoiding accidental fainting."""
        for kind in ["full", "damaged", "one", "fainted"]:
            with self.subTest(kind=kind):
                self.state(evs=[252, 0, 0, 0, 0, 0], friendship=70)
                old_max = get_max_hp(self.fresh())
                old_hp = {"full": old_max, "damaged": old_max - 20, "one": 1, "fainted": 0}[kind]
                self.state(current_hp=old_hp, status="psn")
                self.give("Pomeg Berry")
                self.command("Pomeg Berry=3")
                row = self.row()
                new_max = get_max_hp(self.fresh())
                expected = 0 if old_hp == 0 else max(1, old_hp + new_max - old_max)
                self.assertLess(new_max, old_max)
                self.assertEqual(row["current_hp"], expected)
                self.assertEqual(row["status"], "psn")

    def test_invalid_saved_evs_and_friendship_reject_without_spend(self):
        """Invalid historical stat rows cannot be used to bypass the standard caps."""
        for evs, friendship in [([253, 0, 0, 0, 0, 0], 70), ([100] * 6, 70), ([0] * 6, 256), ([0] * 5, 70)]:
            with self.subTest(evs=evs, friendship=friendship):
                self.state(evs=evs, friendship=friendship)
                self.give("Pomeg Berry")
                before = self.trainer.get_item_quantity("Pomeg Berry")
                self.command("Pomeg Berry=3")
                self.assertIn("Invalid saved", self.messages[-1])
                self.assertEqual(self.row()["evs"], evs)
                self.assertEqual(self.trainer.get_item_quantity("Pomeg Berry"), before)

    def test_valid_total_ev_cap_remains_valid(self):
        """Reducing a 510-EV row changes only the intended entry and no other EVs."""
        self.state(evs=[252, 252, 6, 0, 0, 0], friendship=255)
        self.give("Pomeg Berry")
        self.command("Pomeg Berry=3")
        self.assertEqual(self.row()["evs"], [242, 252, 6, 0, 0, 0])

    def test_canonical_party_gap_exact_name_id_and_legacy_syntax(self):
        """Inventory aliases and names/UUIDs preserve canonical party identity."""
        self.give("Oran Berry", 5)
        for args in ["oran-berry=3", "Mew=Oran Berry", f"Oran Berry={self.mon.pk}"]:
            self.state(current_hp=1)
            self.command(args)
            self.assertEqual(self.row()["current_hp"], 11)
        self.state(current_hp=1)
        self.command("Oran Berry=1")
        self.assertEqual(self.row()["current_hp"], 1)
        self.assertEqual(self.trainer.get_item_quantity("Oran Berry"), 2)

    def test_ambiguous_names_and_foreign_owner_cannot_be_fed(self):
        """A species collision needs a slot; another owner's UUID stays ineligible."""
        self.create_mon()
        other = ObjectDB.objects.create(db_key="berry-foreign-" + uuid4().hex)
        trainer = Trainer.objects.create(user=other, trainer_number=Trainer.objects.count() + 1)
        foreign = create_owned_pokemon("Eevee", trainer, 5)
        self.give("Pomeg Berry", 2)
        self.command("Pomeg Berry=Mew")
        self.assertIn("ambiguous", self.messages[-1])
        self.command(f"Pomeg Berry={foreign.pk}")
        self.assertEqual(self.trainer.get_item_quantity("Pomeg Berry"), 2)
        self.assertEqual(self.row()["friendship"], 70)

    def test_egg_box_inactive_fusion_and_stale_owner_rejected(self):
        """All field effects share medicine eligibility, including EV feeding."""
        self.give("Pomeg Berry", 5)
        self.state(is_egg=True)
        self.command("Pomeg Berry=3")
        self.assertIn("eggs", self.messages[-1])
        self.state(is_egg=False)
        PlacementService(self.storage).to_box(self.mon)
        self.command(f"Pomeg Berry={self.mon.pk}")
        PlacementService(self.storage).to_party(self.mon, slot=3)
        PlacementService(self.storage).reserve_for_fusion(self.mon)
        self.command("Pomeg Berry=fusion")
        self.command(f"Pomeg Berry={self.mon.pk}")
        PlacementService(self.storage).return_from_fusion(self.mon, preferred_slot=3)
        other = ObjectDB.objects.create(db_key="changed-berry-owner-" + uuid4().hex)
        trainer = Trainer.objects.create(user=other, trainer_number=Trainer.objects.count() + 1)
        self.state(trainer_id=trainer.pk)
        self.command("Pomeg Berry=3")
        self.assertEqual(self.trainer.get_item_quantity("Pomeg Berry"), 5)
        self.assertEqual(self.row()["friendship"], 70)

    def test_current_fusion_can_receive_recovery_and_ev_berries(self):
        """Current Fusion uses the same persisted Pokemon without slot aliases."""
        PlacementService(self.storage).reserve_for_fusion(self.mon)
        self.character.db.fusion_id = str(self.mon.pk)
        self.state(current_hp=1, evs=[0, 11, 0, 0, 0, 0])
        self.give("Oran Berry")
        self.give("Kelpsy Berry")
        self.command("Oran Berry=fusion")
        self.command("Kelpsy Berry=self")
        row = self.row()
        self.assertEqual((row["current_hp"], row["evs"][1], row["friendship"]), (11, 1, 80))

    def test_battle_guards_missing_inventory_and_bad_selectors(self):
        """Persistent/runtime battle locks and malformed selectors never debit."""
        self.give("Pomeg Berry", 2)
        self.character.db.battle_lock = "berry-test-battle"
        self.command("Pomeg Berry=3")
        self.assertIsNone(FieldBerryUse(self.caller).use("Pomeg Berry", "3"))
        self.character.db.battle_lock = None
        self.caller.ndb.battle_instance = object()
        self.command("Pomeg Berry=3")
        self.caller.ndb.battle_instance = None
        for args in ["Pomeg Berry=3/Tackle", "Pomeg Berry=3/", "Pomeg Berry", "Pomeg Berry=/1"]:
            self.command(args)
        self.command("Kelpsy Berry=3")
        self.assertIn("don't have", self.messages[-1])
        with self.assertRaises(FieldMedicineError):
            FieldBerryUse(self.caller).use("Pomeg Berry", "")
        self.assertEqual(self.trainer.get_item_quantity("Pomeg Berry"), 2)
        self.assertEqual(self.row()["friendship"], 70)

    def test_unallowlisted_berries_never_use_generic_eating(self):
        """Contest, volatile, resist and combat-trigger berries remain held-only."""
        for item in ["Razz Berry", "Bluk Berry", "Persim Berry", "Enigma Berry", "Chilan Berry", "Liechi Berry", "Micle Berry", "Jaboca Berry"]:
            with self.subTest(item=item):
                self.give(item)
                self.command(f"{item}=3")
                self.assertIn("not usable outside battle", self.messages[-1])
                self.assertEqual(self.trainer.get_item_quantity(item), 1)
                self.assertFalse(FieldBerryUse.supports(item))

    def test_stale_hp_ev_and_friendship_cache_never_overwrites_sql(self):
        """Queued UI knowledge is revalidated from the current saved fields."""
        self.mon.evs, self.mon.friendship, self.mon.current_hp = [252, 0, 0, 0, 0, 0], 1, 1
        self.state(evs=[0] * 6, friendship=255, current_hp=self.maximum)
        self.give("Pomeg Berry")
        self.command("Pomeg Berry=3")
        self.assertIn("No item was consumed", self.messages[-1])
        self.assertEqual(self.trainer.get_item_quantity("Pomeg Berry"), 1)
        self.assertEqual((self.mon.evs, self.mon.friendship, self.mon.current_hp), ([0] * 6, 255, self.maximum))

    def test_saved_changes_visible_after_connection_reopen_and_battle_rebuild(self):
        """Reconnect sees EVs/friendship/HP/status/PP, including depleted moves."""
        from django.db import connections

        self.pp_setup()
        self.state(evs=[252, 0, 0, 0, 0, 0], current_hp=1, status="slp", sleep_turns=2)
        for item, args in [("Pomeg Berry", "Pomeg Berry=3"), ("Chesto Berry", "Chesto Berry=3"), ("Leppa Berry", "Leppa Berry=3/4")]:
            self.give(item)
            self.command(args)
        connections.close_all()
        row = self.row()
        self.assertEqual((row["evs"], row["friendship"], row["current_hp"], row["status"], row["sleep_turns"]), ([242, 0, 0, 0, 0, 0], 80, 1, "", None))
        restored = Pokemon.from_dict(build_battle_pokemon_from_model(self.fresh()).to_dict())
        self.assertEqual((restored.hp, restored.max_hp), (1, get_max_hp(self.mon)))
        self.assertEqual([move.pp for move in restored.moves], [0, 10])

    def test_failed_debit_changes_neither_recovery_evs_nor_friendship(self):
        """A rejected inventory debit cannot apply an independent partial effect."""
        self.state(current_hp=1, evs=[252, 0, 0, 0, 0, 0], friendship=70)
        for item in ["Oran Berry", "Pomeg Berry"]:
            self.give(item)
            with patch.object(Trainer, "remove_item", return_value=False):
                self.command(f"{item}=3")
            row = self.row()
            self.assertEqual((row["current_hp"], row["evs"], row["friendship"]), (1, [252, 0, 0, 0, 0, 0], 70))
            self.assertEqual(self.trainer.get_item_quantity(item), 1)

    def test_ev_save_failure_rolls_back_debit_stats_hp_and_identity_map(self):
        """A failure after the EV/HP write rolls back rows and cached Pokemon."""
        self.state(current_hp=1, evs=[252, 0, 0, 0, 0, 0], friendship=70)
        self.give("Pomeg Berry")
        original = OwnedPokemon.save

        def fail_save(mon, *args, **kwargs):
            """Raise after the actual field write to exercise the outer rollback."""
            original(mon, *args, **kwargs)
            if mon.pk == self.mon.pk and "evs" in kwargs.get("update_fields", []):
                raise RuntimeError("injected EV berry write failure")

        with patch.object(OwnedPokemon, "save", fail_save):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                self.command("Pomeg Berry=3")
        row = self.row()
        self.assertEqual((row["evs"], row["friendship"], row["current_hp"]), ([252, 0, 0, 0, 0, 0], 70, 1))
        self.assertEqual((self.mon.evs, self.mon.friendship), (row["evs"], 70))
        self.assertEqual(self.trainer.get_item_quantity("Pomeg Berry"), 1)

    def test_berry_pp_save_failure_rolls_back_inventory_and_pp(self):
        """Leppa keeps the medicine PP effect/debit rollback guarantee."""
        self.pp_setup()
        self.give("Leppa Berry")
        original = ActiveMoveslot.save

        def fail_save(slot, *args, **kwargs):
            """Fail a selected move's durable PP save."""
            original(slot, *args, **kwargs)
            raise RuntimeError("injected berry PP write failure")

        with patch.object(ActiveMoveslot, "save", fail_save):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                self.command("Leppa Berry=3/4")
        self.assertEqual(self.pp(), [0, 0])
        self.assertEqual(self.trainer.get_item_quantity("Leppa Berry"), 1)

    def race(self, *actions):
        """Use independent SQL connections competing at the field transaction."""
        from django.db import close_old_connections, connections

        barrier = Barrier(len(actions))

        def run(action):
            """Close every worker connection even if a command raises."""
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return action()
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            return list(pool.map(run, actions))

    def test_competing_ev_feeds_cannot_spend_last_berry_twice(self):
        """A single inventory unit can remove only ten EVs and raise friendship once."""
        self.state(evs=[252, 0, 0, 0, 0, 0], friendship=70)
        self.give("Pomeg Berry")
        self.race(lambda: self.command("Pomeg Berry=3"), lambda: self.command("Pomeg Berry=3"))
        self.assertEqual(self.row()["evs"], [242, 0, 0, 0, 0, 0])
        self.assertEqual(self.row()["friendship"], 80)
        self.assertEqual(self.trainer.get_item_quantity("Pomeg Berry"), 0)

    def test_competing_terminal_feeds_recheck_fresh_state_and_repeated_no_effect(self):
        """The second command sees capped friendship and zero EVs without a debit."""
        self.state(evs=[0, 1, 0, 0, 0, 0], friendship=254)
        self.give("Kelpsy Berry", 2)
        self.race(lambda: self.command("Kelpsy Berry=3"), lambda: self.command("Kelpsy Berry=3"))
        self.command("Kelpsy Berry=3")
        self.assertEqual(self.row()["evs"], [0] * 6)
        self.assertEqual(self.row()["friendship"], 255)
        self.assertEqual(self.trainer.get_item_quantity("Kelpsy Berry"), 1)

    def test_two_effective_concurrent_feeds_accumulate_without_lost_updates(self):
        """Both distinct commands commit their own reduction and friendship gain."""
        self.state(evs=[252, 0, 0, 0, 0, 0], friendship=70)
        self.give("Pomeg Berry", 2)
        self.race(lambda: self.command("Pomeg Berry=3"), lambda: self.command("Pomeg Berry=3"))
        self.assertEqual(self.row()["evs"], [232, 0, 0, 0, 0, 0])
        self.assertEqual(self.row()["friendship"], 90)
        self.assertEqual(self.trainer.get_item_quantity("Pomeg Berry"), 0)

    def test_recorded_ordinary_field_feeding_walkthrough(self):
        """Print exact command output and saved effects for the acceptance report."""
        self.pp_setup()
        self.state(evs=[252, 0, 0, 0, 0, 0], friendship=70, current_hp=1, status="psn")
        steps = []
        for item, args in [("Oran Berry", "Oran Berry=3"), ("Pecha Berry", "Pecha Berry=3"), ("Leppa Berry", "Leppa Berry=3/Water Gun"), ("Pomeg Berry", "Pomeg Berry=3")]:
            self.give(item)
            before = self.row()
            self.command(args)
            after = self.row()
            self.assertTrue(self.messages[-1].startswith("Used "), self.messages[-1])
            self.assertEqual(self.trainer.get_item_quantity(item), 0)
            steps.append({"command": "+use " + args, "output": self.messages[-1],
                          "before": {k: before[k] for k in ("current_hp", "status", "evs", "friendship")},
                          "after": {k: after[k] for k in ("current_hp", "status", "evs", "friendship")},
                          "pp": self.pp(), "max_hp": get_max_hp(self.fresh()), "remaining_item": 0})
        print("FIELD_BERRY_WALKTHROUGH " + json.dumps(steps))


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from evennia.commands.command import Command

        with patch.object(evennia, "Command", Command):
            from commands.player.cmd_inventory import CmdUseItem
        from evennia.objects.models import ObjectDB

        from pokemon.battle.battledata import Pokemon
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon, get_max_hp, get_stats
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot, MovePPBoost
        from pokemon.models.storage import UserStorage
        from pokemon.models.trainer import Trainer
        from pokemon.services.field_berries import FieldBerryUse
        from pokemon.services.field_items import FieldMedicineError, FieldMedicineUse
        from pokemon.services.placement import PlacementService
        from utils.pokemon_utils import build_battle_pokemon_from_model

        unittest.main(verbosity=2)

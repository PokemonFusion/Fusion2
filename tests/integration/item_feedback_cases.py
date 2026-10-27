"""Ordinary item purchases, PP sheets and evolution notices on disposable SQL."""

import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import item_availability_cases as acquisition

EVIDENCE = []


class ItemFeedbackCases(unittest.TestCase):
    """Keep production command/menu/model behavior while capturing transport."""

    tearDown = acquisition.AcquisitionCases.tearDown
    native = acquisition.AcquisitionCases.native
    state = acquisition.AcquisitionCases.state
    command = acquisition.AcquisitionCases.command
    reply = acquisition.AcquisitionCases.reply

    def setUp(self):
        """Author finite stock and a legal native target in a gapped party."""
        acquisition.AcquisitionCases.setUp(self)
        PlacementService(self.player.storage).to_box(self.mon)
        self.mon = create_owned_pokemon(
            "Squirtle", self.player.trainer, 50, nature="Hardy", ability="Torrent",
            ivs=[0] * 6, evs=[0] * 6, active_move_names=["Tackle", "Water Gun"],
        )
        PlacementService(self.player.storage).to_party(self.mon, slot=3)
        ActiveMoveslot.objects.filter(pokemon=self.mon, slot=2).update(slot=3)
        self.mons.append(self.mon)
        self.room.db.store_buy_only = True
        self.room.db.store_inventory = {
            "PP Up": {"price": 9800, "quantity": 3},
            "PP Max": {"price": 15000, "quantity": 2},
            "Fire Stone": {"price": 3000, "quantity": 2},
        }

    def record(self, name, args=""):
        """Retain exact ordinary input/output and independent SQL state."""
        before, start = self.state(), len(self.player.messages)
        result = self.command(name, args)
        EVIDENCE.append({"command": "+" + name + (" " + args if args else ""),
                         "before": before, "after": self.state(),
                         "messages": list(map(str, self.player.messages[start:]))})
        return result

    def buy(self, name):
        """Buy from existing finite offers without replacing stock or granting bags."""
        before = self.state()
        self.record("store")
        for text in ("1", name + " 1", "back", "q"):
            start = len(self.player.messages)
            self.reply(text)
            EVIDENCE.append({"command": text, "messages": list(map(str, self.player.messages[start:]))})
        after = self.state()
        self.assertEqual(after["wallet"], before["wallet"] - before["stock"][name]["price"])
        self.assertEqual(after["stock"][name]["quantity"], before["stock"][name]["quantity"] - 1)
        self.assertIn(name, self.record("inventory"))

    def boost(self):
        """Use a full move name and a real gapped active slot from the normal prompt."""
        self.buy("PP Up")
        self.buy("PP Max")
        self.record("use", "PP Up=3")
        self.assertIn("3. Watergun", self.player.messages[-1])
        self.record("use", "Water Gun")
        self.record("use", "PP Max=3")
        self.record("use", "1")

    def fresh_transport(self):
        """Close SQL connections/identity caches and bind a fresh player transport."""
        from django.db import connections

        character_id, trainer_id, storage_id = self.player.pk, self.player.trainer.pk, self.player.storage.pk
        connections.close_all()
        for mon in self.mons:
            OwnedPokemon.flush_cached_instance(mon)
        ObjectDB.flush_cached_instance(self.player.character)
        character = ObjectDB.objects.get(pk=character_id)
        self.player = acquisition.AcquisitionPlayer(character, Trainer.objects.get(pk=trainer_id),
                                                     UserStorage.objects.get(pk=storage_id))
        self.player.pk, self.player.location = character.pk, self.room
        self.players[0] = self.player
        self.mon = OwnedPokemon.objects.get(pk=self.mon.pk)
        EVIDENCE.append({"event": "fresh_SQL_connection_and_player_transport",
                         "actual_socket_reconnect": False, "after": self.state()})

    def assert_sheets(self, tackle=56, water=30):
        """Both registered party display modes must agree with saved capacity."""
        before = self.state()
        for args in ("3", "/moves 3"):
            output = self.record("party", args)
            self.assertIn(f"Tackle ({tackle}/56 PP)", output)
            self.assertIn(f"Watergun ({water}/30 PP)", output)
        self.assertEqual(self.state(), before, "Displaying PP must not alter any saved state")

    def test_purchase_boost_full_moves_and_fresh_player_transport(self):
        """Reproduce the released defect with real bag debits and gapped move slots."""
        self.boost()
        self.mon.pp_bonuses = {"tackle": 1, "watergun": 2}  # deliberately stale display adapter
        self.assert_sheets()
        self.fresh_transport()
        self.assert_sheets()
        self.assertEqual(self.player.trainer.get_item_quantity("PP Up"), 0)
        self.assertEqual(self.player.trainer.get_item_quantity("PP Max"), 0)

    def test_depleted_and_zero_current_pp_are_not_refilled_by_display(self):
        """The maximum includes boosts while current PP retains real spending."""
        self.boost()
        ActiveMoveslot.objects.filter(pokemon=self.mon, slot=1).update(current_pp=0)
        ActiveMoveslot.objects.filter(pokemon=self.mon, slot=3).update(current_pp=7)
        self.fresh_transport()
        self.assert_sheets(tackle=0, water=7)

    def test_unknown_current_pp_displays_capacity_without_saving_a_refill(self):
        """Preserve the existing null-current presentation fallback and SQL value."""
        self.boost()
        ActiveMoveslot.objects.filter(pokemon=self.mon).update(current_pp=None)
        self.fresh_transport()
        self.assert_sheets()
        self.assertTrue(all(pp is None for pp in ActiveMoveslot.objects.filter(pokemon=self.mon).values_list("current_pp", flat=True)))

    def test_legacy_raw_bonus_display_uses_the_existing_capacity_policy(self):
        """A readable noncanonical raw bonus is displayed without silent migration."""
        slot = ActiveMoveslot.objects.get(pokemon=self.mon, slot=1)
        MovePPBoost.objects.create(pokemon=self.mon, move=slot.move, bonus_pp=1)
        ActiveMoveslot.objects.filter(pk=slot.pk).update(current_pp=12)
        self.fresh_transport()
        before = self.state()
        self.assertIn("Tackle (12/36 PP)", self.record("party", "/moves 3"))
        self.assertEqual(self.state(), before)

    def evolution_target(self, nickname=""):
        """Prepare a native full-ID target; only acquisition uses player commands."""
        PlacementService(self.player.storage).to_box(self.mon)
        self.mon = self.native("Vulpix", 3)
        self.mon.nickname = nickname
        self.mon.save(update_fields=["nickname"])
        self.buy("Fire Stone")
        return str(self.mon.pk) + " Fire Stone"

    def test_native_evolution_notice_and_replay_after_fresh_SQL(self):
        """Report the old species, preserve the transition, and never repeat success."""
        args = self.evolution_target()
        before = self.state()
        self.assertEqual(self.record("evolve", args), "Vulpix evolved into Ninetales!")
        self.assertEqual(self.player.trainer.get_item_quantity("Fire Stone"), 0)
        after = self.state()
        self.fresh_transport()
        self.assertIn("Ninetales", self.record("party", "3"))
        start = len(self.player.messages)
        self.record("evolve", args)
        self.assertFalse(any("evolved into" in str(m) for m in self.player.messages[start:]))
        self.assertIn("already completed", self.player.messages[-1])
        self.assertEqual(self.state(), after)
        previous = next(row for row in before["owned"] if row["pk"] == self.mon.pk)
        current = next(row for row in after["owned"] if row["pk"] == self.mon.pk)
        for key, value in previous.items():
            if key not in {"species", "ability", "type_", "flags"}:
                self.assertEqual(current[key], value, key)

    def test_evolution_retains_nickname_and_correct_destination(self):
        """A nickname remains the source display identity and survives the evolution."""
        args = self.evolution_target("Ember Fox")
        self.assertEqual(self.record("evolve", args), "Ember Fox evolved into Ninetales!")
        self.fresh_transport()
        self.assertEqual((self.mon.nickname, self.mon.species), ("Ember Fox", "Ninetales"))

    def test_outer_commit_notifies_once_after_model_publication(self):
        """An enclosing transaction still controls when successful wording is visible."""
        from django.db import transaction

        args = self.evolution_target()
        start = len(self.player.messages)
        with transaction.atomic():
            self.record("evolve", args)
            self.assertEqual(OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("species", flat=True).get(), "Ninetales")
            self.assertFalse(any("evolved into" in str(m) for m in self.player.messages[start:]))
        self.assertEqual(self.player.messages[start:], ["Vulpix evolved into Ninetales!"])
        EVIDENCE.append({"event": "outer_commit_notice", "messages": self.player.messages[start:], "after": self.state()})

    def test_outer_rollback_is_silent_and_retry_keeps_original_name(self):
        """Real temporary SQL changes roll back without publishing a false success."""
        from django.db import transaction

        args = self.evolution_target()
        before, start = self.state(), len(self.player.messages)
        with self.assertRaisesRegex(RuntimeError, "feedback outer rollback"):
            with transaction.atomic():
                self.record("evolve", args)
                self.assertEqual(OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("species", flat=True).get(), "Ninetales")
                raise RuntimeError("feedback outer rollback")
        self.assertEqual(self.state(), before)
        self.assertFalse(any("evolved into" in str(m) for m in self.player.messages[start:]))
        self.assertEqual(self.record("evolve", args), "Vulpix evolved into Ninetales!")

    def test_post_save_failure_keeps_item_species_and_success_silent(self):
        """A genuine post-write failure rolls back the service and never sends success."""
        args = self.evolution_target()
        before, start = self.state(), len(self.player.messages)
        original = OwnedPokemon.save

        def fail_after_save(mon, *args, **kwargs):
            """Perform real SQL then fail inside the evolution transaction."""
            original(mon, *args, **kwargs)
            if mon.pk == self.mon.pk and mon.species == "Ninetales":
                raise RuntimeError("feedback post-save fixture")

        with patch.object(OwnedPokemon, "save", fail_after_save):
            self.record("evolve", args)
        self.assertEqual(self.state(), before)
        self.assertFalse(any("evolved into" in str(m) for m in self.player.messages[start:]))
        self.assertIn("Evolution failed", self.player.messages[-1])


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        acquisition.load_runtime()
        import evennia
        from evennia.commands.command import Command
        with patch.object(evennia, "Command", Command):
            from commands.player import cmd_sheet
        acquisition.COMMANDS["party"] = (cmd_sheet, cmd_sheet.CmdSheetPokemon)
        from evennia.objects.models import ObjectDB
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot, MovePPBoost
        from pokemon.models.storage import UserStorage
        from pokemon.models.trainer import Trainer
        from pokemon.services.placement import PlacementService
        try:
            result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ItemFeedbackCases))
        finally:
            destination = os.environ.get("PF2_ITEM_FEEDBACK_EVIDENCE")
            if destination:
                Path(destination).write_text(json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())

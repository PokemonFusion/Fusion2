"""Real hunt/capture/held inventory routes for the opt-in Rattata/Oran source."""

import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import item_availability_cases as acquisition

EVIDENCE = []


class WildHeldItemCases(unittest.TestCase):
    """Adapt only session transport and controlled authoring/roll preconditions."""

    setUp = acquisition.AcquisitionCases.setUp
    tearDown = acquisition.AcquisitionCases.tearDown
    native = acquisition.AcquisitionCases.native
    state = acquisition.AcquisitionCases.state
    command = acquisition.AcquisitionCases.command

    def start(self, *, item="Oran Berry", chance=100, species="Rattata"):
        """Run normal +hunt using an explicit single-entry authored chart."""
        self.room.db.allow_hunting, self.room.db.itemfinder_rate = True, 0
        self.room.db.npc_chance, self.room.db.encounter_rate = 0, 100
        self.room.db.hunt_chart = [{"name": species, "min_level": 5, "max_level": 5,
            "weight": 1, "held_item": item, "held_item_chance": chance}]
        self.command("hunt")
        self.session = self.player.ndb.battle_instance
        self.assertIsNotNone(self.session)
        return self.session.battle.participants[1].active[0]

    def rebuild(self):
        """Persist and reconstruct the actual wild session, including explicit empty item."""
        identifier = self.session.battle_id
        self.session._sync_active_battle_state()
        self.session._persist_turn_state()
        battle_handler.unregister(self.session)
        self.player.ndb.battle_instance = None
        self.room.ndb.battle_instances = {}
        self.session = BattleSession.restore(self.room, identifier)
        self.assertIsNotNone(self.session)
        return self.session.battle.participants[1].active[0]

    def capture(self):
        """Use a real bag Master Ball through +item and read its canonical receipt."""
        foe = self.session.battle.participants[1].active[0]
        identity = foe.model_id.removeprefix("encounter:")
        self.player.trainer.add_item("Master Ball")  # capture fixture setup, not item-source proof
        self.command("item", "Master Ball")
        receipt = CaptureReceipt.objects.get(encounter_id=identity)
        self.assertEqual(self.player.trainer.get_item_quantity("Master Ball"), 0)
        return OwnedPokemon.objects.get(pk=receipt.owned_id), receipt

    def test_hunt_rebuild_capture_remove_feed_and_reload(self):
        """The acquired berry travels through actual encounter, capture, bag and +use."""
        self.mon.current_hp = 1
        self.mon.save(update_fields=["current_hp"])
        before = self.state()
        foe = self.start()
        self.assertEqual(normalize_name(getattr(foe.item, "name", foe.item)), "oranberry")
        identity = foe.model_id.removeprefix("encounter:")
        self.assertEqual(EncounterPokemon.objects.filter(pk=identity).values_list("held_item", flat=True).get(), "Oran Berry")
        foe = self.rebuild()
        self.assertEqual(normalize_name(getattr(foe.item, "name", foe.item)), "oranberry")
        caught, receipt = self.capture()
        self.assertEqual(normalize_name(caught.held_item), "oranberry")
        self.assertIn("oranberry", normalize_name(self.command("party", str(receipt.party_slot))))
        self.command("hold", str(receipt.party_slot) + "=")
        self.assertEqual(self.player.trainer.get_item_quantity("Oran Berry"), 1)
        self.assertIn("Oran Berry", self.command("inventory"))
        self.command("use", "Oran Berry=3")
        self.assertEqual(self.player.trainer.get_item_quantity("Oran Berry"), 0, self.player.messages[-6:])
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("current_hp", flat=True).get(), 11)
        self.assertEqual(OwnedPokemon.objects.filter(pk=caught.pk).values_list("held_item", flat=True).get(), "")
        from django.db import connections
        connections.close_all()
        EVIDENCE.append({"label": "ordinary-wild-held-acquisition", "before": before, "after": self.state(),
            "encounter": identity, "owned": str(caught.pk), "party_slot": receipt.party_slot,
            "commands": ["+hunt", "checkpoint rebuild", "+item Master Ball", "+party " + str(receipt.party_slot),
                "+hold " + str(receipt.party_slot) + "=", "+inventory", "+use Oran Berry=3", "SQL reload"],
            "messages": list(map(str, self.player.messages))})

    def test_eaten_item_stays_empty_through_rebuild_and_capture(self):
        """A real held-item consumer cannot be undone by old encounter metadata."""
        foe = self.start()
        foe.hp = 1  # controlled held-consumption precondition, distinct from player acquisition flow
        self.assertTrue(foe.eat_item())
        self.assertEqual(foe.hp, 11)
        self.assertFalse(foe.item)
        self.assertFalse(self.rebuild().item)
        caught, _ = self.capture()
        self.assertEqual(caught.held_item, "")

    def test_removed_item_stays_empty_through_capture(self):
        """The ordinary removal consumer's explicit empty state is authoritative."""
        foe = self.start()
        self.assertTrue(foe.take_item())
        self.assertFalse(self.rebuild().item)
        caught, _ = self.capture()
        self.assertEqual(caught.held_item, "")

    def test_capture_replay_does_not_duplicate_owned_item(self):
        """An old capture callback returns its receipt without minting another berry."""
        foe = self.start()
        caught, receipt = self.capture()
        count = OwnedPokemon.objects.count()
        result = finalize_wild_capture(target_poke=foe, player=self.player, trainer=self.player.trainer)
        self.assertTrue(result.owned_pokemon_id.endswith(str(caught.pk)))
        self.assertEqual(OwnedPokemon.objects.count(), count)
        self.assertEqual(CaptureReceipt.objects.filter(encounter_id=receipt.encounter_id).count(), 1)
        self.assertEqual(normalize_name(caught.held_item), "oranberry")

    def test_invalid_excluded_and_default_empty_sources(self):
        """Authoring one source does not make every chart item or species a drop."""
        for item, chance, species in (("Oran Berry", 0, "Rattata"), ("Oran Berry", True, "Rattata"),
                ("Leader's Crest", 100, "Rattata"), ("Mega Ring", 100, "Rattata"),
                ("Oran Berry", 100, "Pikachu")):
            self.assertFalse(self.start(item=item, chance=chance, species=species).item)
            self.session.end()
            self.player.ndb.last_hunt_time = None

    def test_encounter_save_failure_never_spawns_a_phantom_item(self):
        """A selected item requires real encounter persistence before battle startup."""
        with patch("pokemon.battle.pokemon_factory.create_encounter_pokemon", side_effect=RuntimeError("encounter fixture")):
            with self.assertRaisesRegex(RuntimeError, "encounter fixture"):
                self.start()
        self.assertIsNone(self.player.ndb.battle_instance)

    def test_noitem_room_keeps_the_reviewed_wild_source_empty(self):
        """A reviewed chart cannot bypass the room's explicit item restriction."""
        self.room.db.noitem = True
        self.assertFalse(self.start().item)

    def test_failed_capture_commit_preserves_item_and_ball(self):
        """Actual capture receipt failure rolls back the original item-bearing encounter."""
        foe = self.start()
        before = OwnedPokemon.objects.count()
        self.player.trainer.add_item("Master Ball")
        attempt = WildCaptureAttempt(target_poke=foe, player=self.player,
            trainer=self.player.trainer, battle_context=self.session, ball_name="Master Ball")
        with patch.object(CaptureReceipt.objects, "create", side_effect=RuntimeError("capture receipt fixture")):
            with self.assertRaisesRegex(RuntimeError, "capture receipt fixture"):
                attempt.resolve(roll=lambda: CaptureOutcome(True, 4, False),
                    consume_ball=lambda: self.player.trainer.remove_item("Master Ball"))
        self.assertEqual(OwnedPokemon.objects.count(), before)
        self.assertEqual(self.player.trainer.get_item_quantity("Master Ball"), 1)
        self.assertEqual(EncounterPokemon.objects.filter(pk=foe.model_id.removeprefix("encounter:")).values_list("held_item", flat=True).get(), "Oran Berry")


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        acquisition.load_runtime()
        import evennia
        from evennia.commands.command import Command
        with patch.object(evennia, "Command", Command):
            from commands.player import cmd_battle_item, cmd_sheet
        acquisition.COMMANDS["item"] = (cmd_battle_item, cmd_battle_item.CmdBattleItem)
        acquisition.COMMANDS["party"] = (cmd_sheet, cmd_sheet.CmdSheetPokemon)
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle.capture import CaptureOutcome
        from pokemon.battle.handler import battle_handler
        from pokemon.models.core import OwnedPokemon, EncounterPokemon
        from pokemon.models.storage import CaptureReceipt
        from pokemon.names import normalize_name
        from pokemon.services.capture import WildCaptureAttempt, finalize_wild_capture

        try:
            result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(WildHeldItemCases))
        finally:
            if os.environ.get("PF2_WILD_HELD_EVIDENCE"):
                Path(os.environ["PF2_WILD_HELD_EVIDENCE"]).write_text(json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())

"""Real EvMenu, saved Fusion cards and HP output in disposable PostgreSQL.

An explicit PF2_TEST_POSTGRES_DSN is mandatory. No migrations, running service
operations or live game rows are touched. UI transports are captured locally.
"""

from __future__ import annotations

import json
import os
import pathlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres

EVIDENCE = {}


class MenuCmdsets:
    """Record real EvMenu command sets on a transport-only test character."""

    def __init__(self):
        """Start without an input override."""
        self.active = []

    def add(self, cmdset, **kwargs):
        """Accept Evennia's actual populated menu command set."""
        self.active.append(cmdset)

    def remove(self, cls):
        """Release the menu's command override on exit."""
        self.active = [cmdset for cmdset in self.active if not isinstance(cmdset, cls)]


class PlayerView:
    """Use real character attributes/models while capturing session messages."""

    def __init__(self, character, trainer, storage):
        """Bind a real database character without starting an Evennia server."""
        self.character = character
        self.id = character.pk
        self.key = character.key
        self.name = self.key
        self.db, self.ndb = character.db, character.ndb
        self.attributes = character.attributes
        self.trainer, self.storage = trainer, storage
        self.cmdset = MenuCmdsets()
        self.messages = []

    def msg(self, text, **kwargs):
        """Capture the same menu output a session would receive."""
        self.messages.append(text[0] if isinstance(text, tuple) else text)


class UICases(unittest.TestCase):
    """Exercise actual menu input, persistence, character ownership and rendering."""

    def setUp(self):
        """Create isolated ordinary player state and a canonical party member."""
        self.character = ObjectDB.objects.create(db_key="UI QA " + uuid4().hex[:8])
        self.trainer = Trainer.objects.create(user=self.character, trainer_number=Trainer.objects.count() + 1)
        self.storage = UserStorage.objects.create(user=self.character)
        self.player = PlayerView(self.character, self.trainer, self.storage)
        self.owned = create_owned_pokemon(
            "Pikachu", self.trainer, 5, nature="Hardy", ability="Static", ivs=[0] * 6,
            evs=[0] * 6, active_move_names=["Thundershock"],
        )

    def tearDown(self):
        """Release any real menu left open by invalid-input or busy-state tests."""
        menu = self.player.ndb._evmenu
        if menu:
            menu.close_menu()

    def capture(self):
        """Create a real capture with reduced PP and a durable prompt intent."""
        encounter = create_encounter_pokemon(
            species="Rattata", level=5, source_kind="wild", nature="Hardy",
            ivs=[0] * 6, evs=[0] * 6, current_hp=1, move_names=["Quickattack"], move_pp=[2],
        )
        target = Pokemon("Rattata", hp=1, max_hp=get_max_hp(encounter), model_id=f"encounter:{encounter.pk}")
        result = finalize_wild_capture(target_poke=target, player=self.player, trainer=self.trainer)
        return result, target

    def reply(self, text):
        """Route input through Evennia's actual bound menu command."""
        command = CmdEvMenuNode()
        command.caller, command.raw_string, command.session = self.player, text, None
        command.func()

    def test_yes_with_spaces_names_only_the_selected_catch(self):
        """Two same-species catches must retain distinct persistent identities."""
        first, _ = self.capture()
        second, _ = self.capture()
        first_id = first.owned_pokemon_id.split(":", 1)[1]
        second_id = second.owned_pokemon_id.split(":", 1)[1]
        self.assertTrue(start_capture_nickname(self.player))
        self.assertTrue(self.player.cmdset.active)
        self.reply("yes")
        self.reply("Little Spark")
        self.reply("no")
        self.assertIsNone(self.player.ndb._evmenu)
        self.assertFalse(self.player.cmdset.active)
        self.assertEqual(OwnedPokemon.objects.filter(pk=first_id).values_list("nickname", flat=True).get(), "Little Spark")
        self.assertEqual(OwnedPokemon.objects.filter(pk=second_id).values_list("nickname", flat=True).get(), "")
        self.assertEqual(CaptureNicknames(self.player).pending(), [])
        EVIDENCE["nickname_yes_no"] = "\n".join(self.player.messages)

    def test_decline_and_cancel_leave_species_name(self):
        """Both ways of keeping the default name cleanly release the input menu."""
        for answer in ("no", "cancel"):
            with self.subTest(answer=answer):
                result, _ = self.capture()
                self.assertTrue(start_capture_nickname(self.player))
                if answer == "cancel":
                    self.reply("yes")
                self.reply(answer)
                identifier = result.owned_pokemon_id.split(":", 1)[1]
                self.assertEqual(OwnedPokemon.objects.filter(pk=identifier).values_list("nickname", flat=True).get(), "")
                self.assertFalse(self.player.cmdset.active)

    def test_invalid_names_reprompt_without_changing_saved_state(self):
        """Length, blank, color and control input are rejected; Unicode is valid."""
        result, _ = self.capture()
        identifier = result.owned_pokemon_id.split(":", 1)[1]
        self.assertTrue(start_capture_nickname(self.player))
        self.reply("yes")
        for name in ("", "X" * 51, "|rRed", "Two\nLines"):
            self.reply(name)
            self.assertEqual(self.player.ndb._evmenu.nodename, "nickname_enter")
            self.assertEqual(OwnedPokemon.objects.filter(pk=identifier).values_list("nickname", flat=True).get(), "")
        self.reply("Éclair Jr.")
        self.assertEqual(OwnedPokemon.objects.filter(pk=identifier).values_list("nickname", flat=True).get(), "Éclair Jr.")

    def test_prompt_is_queued_once_and_can_resume_after_quit(self):
        """Capture replay and reconnect-style menu loss cannot duplicate a choice."""
        result, target = self.capture()
        finalize_wild_capture(target_poke=target, player=self.player, trainer=self.trainer)
        self.assertEqual(len(CaptureNicknames(self.player).pending()), 1)
        self.assertTrue(start_capture_nickname(self.player))
        self.reply("quit")
        self.assertEqual(len(CaptureNicknames(self.player).pending()), 1)
        resumed = PlayerView(ObjectDB.objects.get(pk=self.character.pk), self.trainer, self.storage)
        self.assertTrue(start_capture_nickname(resumed))
        self.reply("no")
        self.assertEqual(CaptureNicknames(resumed).pending(), [])

    def test_busy_battle_or_other_menu_is_not_interrupted(self):
        """A nickname choice only takes control after combat/menu input is free."""
        self.capture()
        self.player.db.battle_lock = "qa-active-battle"
        self.assertFalse(start_capture_nickname(self.player))
        del self.player.db.battle_lock
        self.player.ndb._evmenu = SimpleNamespace()
        self.assertFalse(start_capture_nickname(self.player))
        del self.player.ndb._evmenu
        self.player.attributes.add("_menutree_saved", (object, ("menus.some_other_menu",), {}))
        self.assertFalse(start_capture_nickname(self.player))
        self.player.attributes.remove("_menutree_saved")

    def test_nickname_command_resumes_persisted_menu_after_memory_loss(self):
        """Saved menu state and +nickname recover a disconnected input prompt."""
        self.capture()
        self.assertTrue(start_capture_nickname(self.player))
        self.reply("yes")
        self.assertIsNotNone(self.player.attributes.get("_menutree_saved"))
        del self.player.ndb._evmenu
        self.player.cmdset.active.clear()
        command = CmdCaptureNickname()
        self.assertEqual(command.key, "+nickname")
        command.caller = self.player
        command.func()
        self.assertIsNotNone(self.player.ndb._evmenu)
        self.reply("yes")
        self.reply("Resumed Friend")
        self.assertEqual(CaptureNicknames(self.player).pending(), [])
        self.assertIsNone(self.player.attributes.get("_menutree_saved"))

    def test_released_catch_is_not_replaced_with_a_different_pokemon(self):
        """If the catch disappears, name input must not select another by species."""
        first, _ = self.capture()
        second, _ = self.capture()
        caught = OwnedPokemon.objects.get(pk=first.owned_pokemon_id.split(":", 1)[1])
        PlacementService(self.storage).release(caught)
        self.assertTrue(start_capture_nickname(self.player))
        self.reply("yes")
        self.reply("Wrong Catch")
        self.reply("no")
        remaining = OwnedPokemon.objects.get(pk=second.owned_pokemon_id.split(":", 1)[1])
        self.assertEqual(remaining.nickname, "")

    def test_name_write_is_owner_scoped_and_does_not_touch_hp_pp(self):
        """Only nickname changes, and a second character cannot rename this catch."""
        result, _ = self.capture()
        identifier = result.owned_pokemon_id.split(":", 1)[1]
        before = OwnedPokemon.objects.filter(pk=identifier).values().get()
        other = ObjectDB.objects.create(db_key="Other UI " + uuid4().hex[:8])
        other_trainer = Trainer.objects.create(user=other, trainer_number=Trainer.objects.count() + 1)
        other_player = PlayerView(other, other_trainer, UserStorage.objects.create(user=other))
        other_player.db.pending_capture_nicknames = [{"pokemon_id": result.owned_pokemon_id, "species": "Rattata"}]
        self.assertIsNone(CaptureNicknames(other_player).complete(result.owned_pokemon_id, "Stolen"))
        CaptureNicknames(self.player).complete(result.owned_pokemon_id, "Small Friend")
        after = OwnedPokemon.objects.filter(pk=identifier).values().get()
        self.assertEqual({key: value for key, value in after.items() if key != "nickname"},
                         {key: value for key, value in before.items() if key != "nickname"})
        self.assertEqual(list(OwnedPokemon.objects.get(pk=identifier).activemoveslot_set.values_list("current_pp", flat=True)), [2])

    def test_prompt_queue_failure_rolls_back_capture_without_phantom_cache(self):
        """Prompt intent is saved with capture, including failure after attribute write."""
        count = OwnedPokemon.objects.count()
        original = CaptureNicknames.queue

        def queue_then_fail(service, *args, **kwargs):
            original(service, *args, **kwargs)
            raise RuntimeError("isolated nickname queue failure")

        with patch.object(CaptureNicknames, "queue", queue_then_fail), self.assertRaises(RuntimeError):
            self.capture()
        self.assertEqual(OwnedPokemon.objects.count(), count)
        self.assertEqual(CaptureNicknames(self.player).pending(), [])

    def test_real_battle_cleanup_opens_prompt_after_releasing_battle_lock(self):
        """The production session cleanup hook must bind the actual menu input."""
        room = ObjectDB.objects.create(db_key="UI test room")
        self.player.location = room
        self.trainer.add_item("masterball", 1)
        session = BattleSession(self.player)
        session.start_test_battle(species="Rattata", level=5, debug=False)
        actor, foe = session.battle.participants
        session.battle.execute_item(Action(actor, ActionType.ITEM, foe, item="Master Ball"))
        self.assertIsNone(self.player.ndb._evmenu)
        session.end()
        self.assertIsNone(self.player.db.battle_lock)
        self.assertIsNone(self.player.ndb.battle_instance)
        self.assertIsNotNone(self.player.ndb._evmenu)
        self.reply("no")
        self.assertFalse(self.player.cmdset.active)

    def fusion(self, *, kind="permanent"):
        """Create an active form with deliberately stale legacy character caches."""
        self.storage.reserve_for_fusion(self.owned)
        self.player.db.fusion_id = str(self.owned.pk)
        self.player.db.fusion_kind = kind
        self.player.db.fusion_species = "Pikachu"
        self.player.db.morphology = "Human"
        self.player.db.total_exp = self.owned.total_exp
        self.player.db.trainer_xp = 64 if kind == "temporary" else 125
        self.player.db.hp = self.player.db.max_hp = 999
        self.player.db.level = 99
        self.player.db.exp_to_next = 999
        self.player.db.stats = {key: 999 for key in ("hp", "attack", "defense", "special_attack", "special_defense", "speed")}
        self.player.db.types = ["Fire"]
        self.player.db.nature = "Wrong nature"
        self.player.db.ability = "Wrong ability"
        self.player.db.inventory = {"Ghost Item": 99}
        self.player.db.money = 999
        self.player.attributes.add("sheet_debug", True)
        self.owned.current_hp = 3
        self.owned.status = "par"
        self.owned.held_item = "Oran Berry"
        self.owned.save(update_fields=["current_hp", "status", "held_item"])
        self.trainer.money = 1234
        self.trainer.save(update_fields=["money"])
        self.trainer.add_item("Potion", 2)

    def sheet(self, switches=None):
        """Execute the actual sheet command with real rendering/ANSI conversion."""
        command = CmdSheet()
        command.caller, command.args = self.player, ""
        command.switches = switches or []
        command.parse()
        command.func()
        return parse_ansi(self.player.messages[-1], strip_ansi=True)

    def test_fusion_sheet_uses_model_stats_traits_hp_wallet_and_inventory(self):
        """The full card reflects the active form and canonical trainer resources."""
        self.fusion()
        before = OwnedPokemon.objects.filter(pk=self.owned.pk).values().get()
        text = self.sheet()
        active = build_battle_pokemon_from_model(get_active_fusion_pokemon(self.player))
        for value in ("Electric", "Hardy", "Static", "Oran Berry", "PAR", "Potion", "1,234", "3/18"):
            self.assertIn(value, text)
        self.assertNotIn("Ghost Item", text)
        self.assertNotIn("Wrong ability", text)
        self.assertNotIn("Human", text)
        self.assertNotIn("999", text)
        self.assertIn("91 to next", text)
        self.assertIn(str(active.getStat("atk", True, True)), text)
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.owned.pk).values().get(), before)
        EVIDENCE["fusion_card"] = self.player.messages[-1]

    def test_temporary_fusion_card_uses_effective_battle_level(self):
        """Trainer XP caps a temporary form consistently with actual battle stats."""
        self.fusion(kind="temporary")
        text = self.sheet(["brief"])
        active = build_battle_pokemon_from_model(get_active_fusion_pokemon(self.player))
        self.assertEqual(active.level, 4)
        self.assertIn("Lv 4", text)
        self.assertIn(f"3/{active.max_hp}", text)
        self.assertNotIn("999", text)
        EVIDENCE["temporary_fusion_card"] = self.player.messages[-1]

    def test_inventory_modes_and_screen_reader_use_canonical_resources(self):
        """Both inventory views and screen-reader output use the same real stock."""
        self.fusion()
        self.player.db.inventory = {"Ghost Item": 99}
        for switches in (["inv"], ["inv", "cat"], ["sr"]):
            text = self.sheet(switches)
            self.assertIn("Potion", text)
            self.assertNotIn("Ghost Item", text)
        self.assertNotIn("|W", self.player.messages[-1])
        EVIDENCE["fusion_screen_reader"] = self.player.messages[-1]

    def test_empty_saved_inventory_does_not_show_stale_cache(self):
        """An empty canonical inventory must not fall back to obsolete stock."""
        self.player.db.inventory = {"Ghost Item": 99}
        self.assertEqual(gather_inventory_pairs(self.player), [])
        self.assertNotIn("Ghost Item", self.sheet())


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from evennia.commands.cmdset import CmdSet
        from evennia.commands.command import Command
        from evennia.objects.models import ObjectDB
        from evennia.utils.ansi import parse_ansi
        from evennia.utils.text2html import parse_html

        # Supply real flat API classes without bootstrapping server services.
        with patch.object(evennia, "Command", Command), patch.object(evennia, "CmdSet", CmdSet):
            from evennia.utils.evmenu import CmdEvMenuNode

            from commands.player.cmd_nickname import CmdCaptureNickname
            from commands.player.cmd_sheet import CmdSheet
        from menus.capture_nickname import start_capture_nickname
        from pokemon.battle.battledata import Pokemon
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle.engine import Action, ActionType
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon, get_max_hp
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.storage import UserStorage
        from pokemon.models.trainer import Trainer
        from pokemon.services.capture import finalize_wild_capture
        from pokemon.services.capture_nicknames import CaptureNicknames
        from pokemon.services.encounters import create_encounter_pokemon
        from pokemon.services.placement import PlacementService
        from utils.fusion import get_active_fusion_pokemon
        from utils.inventory_view import gather_inventory_pairs
        from utils.pokemon_utils import build_battle_pokemon_from_model

        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(UICases))
        output = os.environ.get("PF2_UI_QA_OUTPUT")
        if output:
            directory = pathlib.Path(output)
            (directory / "ui-output.json").write_text(json.dumps(EVIDENCE, ensure_ascii=False, indent=2), encoding="utf-8")
            body = "\n".join(f"<h2>{name}</h2><pre>{parse_html(text)}</pre>" for name, text in EVIDENCE.items())
            (directory / "ui-preview.html").write_text(
                "<!doctype html><meta charset='utf-8'><title>Local UI QA</title>"
                "<style>body{background:#111;color:#ddd;padding:24px}pre{white-space:pre-wrap;line-height:1.5}</style>" + body,
                encoding="utf-8",
            )
        raise SystemExit(not result.wasSuccessful())

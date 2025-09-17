"""Tests for automatic turn notifications when characters log in."""

from __future__ import annotations

import importlib.util
import os
import sys
import types

from pokemon.battle.interface import format_turn_banner

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
        sys.path.insert(0, ROOT)


def load_character_module():
        """Load the character typeclass module with fresh stubs."""

        path = os.path.join(ROOT, "typeclasses", "characters.py")
        spec = importlib.util.spec_from_file_location("typeclasses.characters", path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        return mod


def setup_evennia():
        """Install minimal Evennia stubs required by the character module."""

        orig_evennia = sys.modules.get("evennia")
        fake_evennia = types.ModuleType("evennia")
        sys.modules["evennia"] = fake_evennia

        objects_mod = types.ModuleType("evennia.objects")
        objs = types.ModuleType("evennia.objects.objects")

        class DefaultObj:
                def at_pre_move(self, destination, **kwargs):
                        return True

                def at_post_puppet(self):
                        return None

                def msg(self, text):
                        return None

        objs.DefaultObject = DefaultObj
        objs.DefaultCharacter = DefaultObj
        objects_mod.objects = objs
        fake_evennia.objects = objects_mod

        sys.modules["evennia.objects"] = objects_mod
        sys.modules["evennia.objects.objects"] = objs

        utils_mod = types.ModuleType("evennia.utils")
        utils_utils = types.ModuleType("evennia.utils.utils")
        utils_utils.inherits_from = lambda obj, parent: isinstance(obj, parent)
        utils_mod.utils = utils_utils
        sys.modules["evennia.utils"] = utils_mod
        sys.modules["evennia.utils.utils"] = utils_utils

        return orig_evennia


def restore_evennia(orig):
        """Remove Evennia stubs and restore any original module."""

        if orig is not None:
                sys.modules["evennia"] = orig
        else:
                sys.modules.pop("evennia", None)
        sys.modules.pop("evennia.objects.objects", None)
        sys.modules.pop("evennia.objects", None)
        sys.modules.pop("evennia.utils.utils", None)
        sys.modules.pop("evennia.utils", None)


def _make_character_module():
        """Set up the Evennia stubs and return a fresh character module."""

        orig = setup_evennia()
        char_mod = load_character_module()
        return orig, char_mod


def test_post_puppet_sends_turn_banner_when_in_battle():
        orig, char_mod = _make_character_module()
        try:
                char = char_mod.Character()
                char.ndb = types.SimpleNamespace(battle_instance=None)
                char.db = types.SimpleNamespace(battle_id=42)
                char.location = types.SimpleNamespace(ndb=types.SimpleNamespace(battle_instances={42: None}))
                char.execute_cmd = lambda *a, **k: None

                messages: list[str] = []
                char.msg = lambda text: messages.append(text)

                battle = types.SimpleNamespace(turn_count=5)
                state = types.SimpleNamespace(turn=5)
                inst = types.SimpleNamespace(trainers=[char], battle=battle, state=state)
                char.ndb.battle_instance = inst

                char.at_post_puppet()

                assert messages, "Expected a turn notification to be sent"
                assert messages[-1] == format_turn_banner(5)
        finally:
                restore_evennia(orig)


def test_post_puppet_skips_notification_for_nonparticipants():
        orig, char_mod = _make_character_module()
        try:
                char = char_mod.Character()
                char.ndb = types.SimpleNamespace(battle_instance=None)
                char.db = types.SimpleNamespace(battle_id=13)
                char.location = types.SimpleNamespace(ndb=types.SimpleNamespace(battle_instances={}))
                char.execute_cmd = lambda *a, **k: None

                messages: list[str] = []
                char.msg = lambda text: messages.append(text)

                battle = types.SimpleNamespace(turn_count=2)
                state = types.SimpleNamespace(turn=2)
                inst = types.SimpleNamespace(trainers=[], battle=battle, state=state)
                char.ndb.battle_instance = inst

                char.at_post_puppet()

                assert not messages
        finally:
                restore_evennia(orig)

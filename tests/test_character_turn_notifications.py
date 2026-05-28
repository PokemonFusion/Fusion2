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


def test_post_puppet_sends_battle_recap_when_in_battle(monkeypatch):
        orig, char_mod = _make_character_module()
        try:
                char = char_mod.Character()
                char.ndb = types.SimpleNamespace(battle_instance=None)
                char.db = types.SimpleNamespace(battle_id=42)
                char.location = types.SimpleNamespace(ndb=types.SimpleNamespace(battle_instances={42: None}))

                messages: list[str] = []
                char.msg = lambda text: messages.append(text)

                waiting_poke = types.SimpleNamespace(name="Pikachu")

                class Position:
                        pokemon = waiting_poke

                        @staticmethod
                        def getAction():
                                return None

                opponent = types.SimpleNamespace(key="Blue")
                battle = types.SimpleNamespace(
                        turn_count=4,
                        participant_for=lambda pokemon: types.SimpleNamespace(is_ai=False),
                )
                state = types.SimpleNamespace(turn=4, declare={})
                data = types.SimpleNamespace(
                        turndata=types.SimpleNamespace(positions={"A1": Position()})
                )
                inst = types.SimpleNamespace(
                        trainers=[char],
                        teamA=[char],
                        teamB=[opponent],
                        captainA=char,
                        captainB=opponent,
                        battle=battle,
                        state=state,
                        data=data,
                )
                char.ndb.battle_instance = inst

                recap_calls = []
                import pokemon.battle.interface as battle_interface

                monkeypatch.setattr(
                        battle_interface,
                        "send_interface_to",
                        lambda session, target, *, waiting_on=None: recap_calls.append(
                                (session, target, waiting_on)
                        ),
                )

                char.at_post_puppet()

                assert messages[0] == "|wYou are still in battle.|n"
                assert recap_calls == [(inst, char, waiting_poke)]
                assert messages[-1] == format_turn_banner(4)
        finally:
                restore_evennia(orig)


def test_post_puppet_restores_battle_before_recap(monkeypatch):
        orig, char_mod = _make_character_module()
        try:
                char = char_mod.Character()
                char.ndb = types.SimpleNamespace()
                char.db = types.SimpleNamespace(battle_id=99)
                char.location = types.SimpleNamespace(ndb=types.SimpleNamespace(battle_instances={}))

                restored = types.SimpleNamespace(state=object(), captainA=object())
                restore_calls = []

                from pokemon.battle.battleinstance import BattleSession

                monkeypatch.setattr(
                        BattleSession,
                        "ensure_for_player",
                        staticmethod(lambda player: restore_calls.append(player) or restored),
                )

                recap_calls = []
                monkeypatch.setattr(char, "_send_battle_recap", lambda inst: recap_calls.append(inst))

                char.at_post_puppet()

                assert restore_calls == [char]
                assert recap_calls == [restored]
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


def test_at_pre_move_blocks_when_battle_lock_present():
        orig, char_mod = _make_character_module()
        try:
                char = char_mod.Character()
                char.ndb = types.SimpleNamespace(battle_instance=None)
                char.db = types.SimpleNamespace(pvp_locked=False, battle_lock="lock")

                messages: list[str] = []
                char.msg = lambda text: messages.append(text)

                result = char.at_pre_move(object())

                assert result is False
                assert messages[-1] == "You cannot do that during battle."
        finally:
                restore_evennia(orig)


def test_at_pre_move_allows_when_battle_lock_attribute_is_missing():
        orig, char_mod = _make_character_module()
        try:
                class DbHolderLike:
                        """Mimic Evennia .db: missing attributes return None."""

                        def __init__(self):
                                object.__setattr__(self, "_values", {})

                        def __getattribute__(self, name):
                                if name in {"_values", "__class__", "__dict__"}:
                                        return object.__getattribute__(self, name)
                                return object.__getattribute__(self, "_values").get(name)

                        def __setattr__(self, name, value):
                                object.__getattribute__(self, "_values")[name] = value

                        def __delattr__(self, name):
                                object.__getattribute__(self, "_values").pop(name, None)

                db = DbHolderLike()
                assert hasattr(db, "battle_lock")
                assert db.battle_lock is None

                char = char_mod.Character()
                char.ndb = types.SimpleNamespace()
                char.db = db

                messages: list[str] = []
                char.msg = lambda text: messages.append(text)

                result = char.at_pre_move(object())

                assert result is True
                assert not messages
        finally:
                restore_evennia(orig)


def test_at_pre_move_blocks_when_battle_instance_present():
        orig, char_mod = _make_character_module()
        try:
                char = char_mod.Character()
                char.ndb = types.SimpleNamespace(battle_instance=object())
                char.db = types.SimpleNamespace(pvp_locked=False)

                messages: list[str] = []
                char.msg = lambda text: messages.append(text)

                result = char.at_pre_move(object())

                assert result is False
                assert messages[-1] == "You cannot do that during battle."
        finally:
                restore_evennia(orig)


def test_at_pre_move_allows_after_battle_cleanup():
        orig, char_mod = _make_character_module()
        try:
                from pokemon.battle.battleinstance import BattleSession

                room = types.SimpleNamespace(
                        id=7,
                        db=types.SimpleNamespace(battles=[]),
                        ndb=types.SimpleNamespace(battle_instances={}),
                )
                char = char_mod.Character()
                char.id = 101
                char.key = "Test"
                char.ndb = types.SimpleNamespace(battle_instance=None)
                char.db = types.SimpleNamespace(pvp_locked=False)
                char.storage = types.SimpleNamespace(get_party=lambda: [])
                char.location = room

                messages: list[str] = []
                char.msg = lambda text: messages.append(text)

                session = BattleSession(char)
                try:
                        assert hasattr(char.db, "battle_lock")
                        assert char.db.battle_lock == session.battle_id

                        blocked = char.at_pre_move(object())
                        assert blocked is False
                        assert messages[-1] == "You cannot do that during battle."

                        messages.clear()
                        session.end()

                        assert not hasattr(char.db, "battle_lock")
                        assert getattr(char.ndb, "battle_instance", None) is None

                        messages.clear()
                        allowed = char.at_pre_move(object())
                        assert allowed is True
                        assert not messages
                finally:
                        if getattr(char.ndb, "battle_instance", None) is session:
                                session.end()
        finally:
                restore_evennia(orig)

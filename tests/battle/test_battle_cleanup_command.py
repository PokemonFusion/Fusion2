"""Tests for the @battlecleanup administrative command."""

from __future__ import annotations

import importlib
import sys
import types
from datetime import datetime, timezone
from typing import List

import pytest


@pytest.fixture
def cleanup_env(monkeypatch):
    """Load the command module with a lightweight Evennia command stub."""

    orig_evennia = sys.modules.get("evennia")
    fake_evennia = types.ModuleType("evennia")

    class BaseCommand:
        def __init__(self):
            self.caller = None
            self.args = ""
            self.switches: List[str] = []

    fake_evennia.Command = BaseCommand
    fake_evennia.search_object = lambda *a, **k: []
    sys.modules["evennia"] = fake_evennia

    mod = importlib.import_module("commands.admin.cmd_adminbattle")
    mod = importlib.reload(mod)
    monkeypatch.setattr(mod, "_active_battle_room_mapping", lambda: {})

    try:
        yield mod
    finally:
        sys.modules.pop("commands.admin.cmd_adminbattle", None)
        if orig_evennia is not None:
            sys.modules["evennia"] = orig_evennia
        else:
            sys.modules.pop("evennia", None)


class DummyCaller:
    """Simple caller used to capture command output."""

    def __init__(self, location=None):
        self.location = location
        self.messages: List[str] = []

    def msg(self, text):
        self.messages.append(text)


def make_room(battle_ids):
    db = types.SimpleNamespace(battles=list(battle_ids))
    ndb = types.SimpleNamespace()
    return types.SimpleNamespace(key="Alpha Route", id=69, db=db, ndb=ndb)


class SaverListLike:
    """Minimal iterable matching Evennia's serialized list behavior."""

    def __init__(self, values):
        self.values = list(values)

    def __iter__(self):
        return iter(self.values)


def test_battlecleanup_reads_evennia_serialized_battle_lists(cleanup_env):
    mod = cleanup_env
    room = make_room([])
    room.db.battles = SaverListLike([18, "34"])

    assert mod._stored_battle_ids(room) == [18, 34]


def test_battlecleanup_formats_candidate_age(cleanup_env):
    mod = cleanup_env
    created = datetime(2026, 5, 29, 2, 22, tzinfo=timezone.utc)
    now = datetime(2026, 5, 30, 5, 52, tzinfo=timezone.utc)
    candidate = mod.BattleCleanupCandidate(
        battle_id=18,
        room=make_room([18]),
        created_at=created,
        latest_part_at=created,
    )

    assert mod._format_age(created, now=now) == "1d 3h"
    text = mod._format_cleanup_candidates([candidate])
    assert "created=2026-05-29 02:22 UTC" in text
    assert "age=" in text


def test_battlecleanup_lists_live_and_stale_records(cleanup_env, monkeypatch):
    mod = cleanup_env
    room = make_room([77, 88])
    live = types.SimpleNamespace(battle_id=77, room=room, teamA=[], teamB=[])

    monkeypatch.setattr(mod, "_rooms_with_battle_records", lambda extra_room=None: [room])
    monkeypatch.setattr(mod, "battle_handler", types.SimpleNamespace(instances={77: live}))

    cmd = mod.CmdBattleCleanup()
    cmd.caller = DummyCaller(room)
    cmd.switches = ["list"]
    cmd.func()

    text = cmd.caller.messages[-1]
    assert "#77 [LIVE]" in text
    assert "#88 [STALE]" in text
    assert "Alpha Route" in text


def test_battlecleanup_purges_stale_room_record(cleanup_env, monkeypatch):
    mod = cleanup_env
    room = make_room([88])
    trainer = types.SimpleNamespace(db=types.SimpleNamespace(battle_id=88), ndb=types.SimpleNamespace())
    room.ndb.battle_instances = {88: object()}
    room.db.battle_88_data = {"x": 1}
    room.db.battle_88_state = {"turn": 2}
    room.db.battle_88_trainers = {"teamA": [1]}
    room.db.battle_88_temp_pokemon_ids = ["enc-1"]

    deleted_refs = []
    cleared_trainers = []

    monkeypatch.setattr(mod, "_rooms_with_battle_records", lambda extra_room=None: [room])
    monkeypatch.setattr(mod, "battle_handler", types.SimpleNamespace(instances={}))
    monkeypatch.setattr(mod, "search_object", lambda query: [trainer] if query == "#1" else [])
    monkeypatch.setattr(mod, "delete_encounter_by_ref", lambda ref: deleted_refs.append(ref))
    monkeypatch.setattr(mod, "clear_battle_lock", lambda obj: cleared_trainers.append(obj))

    cmd = mod.CmdBattleCleanup()
    cmd.caller = DummyCaller(room)
    cmd.switches = ["purge"]
    cmd.args = "88"
    cmd.func()

    assert "Purged stale battle #88" in cmd.caller.messages[-1]
    assert deleted_refs == ["enc-1"]
    assert cleared_trainers == [trainer]
    assert not hasattr(room.db, "battles")
    assert not hasattr(room.db, "battle_88_data")
    assert not hasattr(room.db, "battle_88_state")
    assert not hasattr(room.db, "battle_88_trainers")
    assert not hasattr(room.db, "battle_88_temp_pokemon_ids")
    assert not hasattr(room.ndb, "battle_instances")
    assert not hasattr(trainer.db, "battle_id")


def test_battlecleanup_uses_live_end_for_live_session(cleanup_env, monkeypatch):
    mod = cleanup_env
    room = make_room([5])
    calls = []

    live = types.SimpleNamespace(
        battle_id=5,
        room=room,
        teamA=[],
        teamB=[],
        end=lambda: calls.append("ended"),
    )

    monkeypatch.setattr(mod, "_rooms_with_battle_records", lambda extra_room=None: [room])
    monkeypatch.setattr(mod, "battle_handler", types.SimpleNamespace(instances={5: live}))

    cmd = mod.CmdBattleCleanup()
    cmd.caller = DummyCaller(room)
    cmd.switches = ["purge"]
    cmd.args = "5"
    cmd.func()

    assert calls == ["ended"]
    assert "aborted via live session cleanup" in cmd.caller.messages[-1]

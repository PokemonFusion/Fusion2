"""Issue #832: persisted battle lifecycle must gate every Adventure action."""

from collections import UserDict
from datetime import timedelta
from types import SimpleNamespace

import pytest

from pokemon.adventures import commands, sessions
from pokemon.adventures.cmdsets import CmdAdventureNorth
from pokemon.adventures.constants import ADVENTURE_SESSION_ATTR, STATE_ACTIVE, STATE_EXPIRED
from tests.adventure.test_adventure_commands import DummyCmdSet
from tests.adventure.test_adventure_sessions import (
    DummyRoom,
    adventure_world,
    fake_session_model,
)


@pytest.mark.parametrize("action", ["choose", "move", "search", "leave", "start"])
def test_active_battle_prevents_service_mutation(adventure_world, action):
    hall, room, player = adventure_world
    session = sessions.start_session(player, "alpha_meadow").session
    assert sessions.move_session(player, "north").ok
    player.db.battle_id = 81
    player.db.battle_lock = 81
    player.ndb.battle_instance = None
    room.db.battles = [81]
    before = (session.current_node, dict(session.objective_progress), dict(session.metadata), session.state)
    result = {
        "choose": lambda: sessions.choose_session_route(player, "wild"),
        "move": lambda: sessions.move_session(player, "north"),
        "search": lambda: sessions.search_session(player),
        "leave": lambda: sessions.leave_session(player),
        "start": lambda: sessions.start_session(player, "alpha_meadow"),
    }[action]()
    assert not result.ok
    assert (session.current_node, session.objective_progress, session.metadata, session.state) == before
    assert player.location is room
    assert room.db.adventure_session_id == session.pk


def test_missing_every_cached_pointer_still_sees_room_battle(adventure_world):
    _hall, room, player = adventure_world
    session = sessions.start_session(player, "alpha_meadow").session
    del player.db.adventure_session_id
    room.db.battles = [92]
    room.db.battle_92_encounter = {"source_type": "adventure", "adventure_session_id": session.pk}
    player.ndb.battle_instance = None
    assert not sessions.move_session(player, "north").ok
    assert not sessions.search_session(player).ok
    assert player.db.adventure_session_id == session.pk


def test_expiry_preserves_owned_battle_and_reconnect_is_nonmoving(adventure_world):
    _hall, room, player = adventure_world
    session = sessions.start_session(player, "alpha_meadow").session
    session.expires_at = sessions._now() - timedelta(minutes=1)
    room.db.battles = [77]
    player.db.battle_id = 77
    player.location = DummyRoom("Reconnect location")
    assert sessions.sync_player_to_active_session(player) is session
    assert player.location is not room
    assert session.state == STATE_ACTIVE
    assert room.db.adventure_session_id == session.pk
    assert sessions.expire_session(session) is False
    del player.db.battle_id
    room.db.battles = []
    assert sessions.expire_session(session) is True
    assert session.state == STATE_EXPIRED


def test_saved_terminal_result_survives_cleanup_and_retries(adventure_world):
    _hall, room, player = adventure_world
    session = sessions.start_session(player, "alpha_meadow").session
    sessions.move_session(player, "north")
    sessions.choose_session_route(player, "wild")
    sessions.queue_encounter_result(session.pk, player, "capture")
    assert not sessions.leave_session(player).ok
    assert not sessions.move_session(player, "north").ok
    assert sessions.expire_session(session) is False
    assert sessions.retry_encounter_results(player).startswith("Encounter resolved")
    assert session.metadata["encounter_result"] == "capture"
    assert player.db.pending_adventure_results == {}
    assert sessions.move_session(player, "north").ok


def test_blocked_return_movement_preserves_ownership(adventure_world):
    _hall, room, player = adventure_world
    session = sessions.start_session(player, "alpha_meadow").session
    player.move_to = lambda *_args, **_kwargs: False
    result = sessions.leave_session(player)
    assert not result.ok
    assert session.state == STATE_ACTIVE
    assert player.db.adventure_session_id == session.pk
    assert room.db.adventure_session_id == session.pk


@pytest.mark.parametrize("evidence", ["lock", "cache", "registry", "index", "storage"])
def test_each_battle_identity_independently_blocks_actions(adventure_world, monkeypatch, evidence):
    """Losing other identities cannot make a surviving battle safe to bypass."""
    from pokemon.battle.handler import battle_handler

    _hall, room, player = adventure_world
    session = sessions.start_session(player, "alpha_meadow").session
    battle = SimpleNamespace(battle_id=81, _ended=False)
    monkeypatch.setattr(battle_handler, "for_player", lambda _player: None)
    if evidence == "lock":
        player.db.battle_lock = 81
    elif evidence == "cache":
        player.ndb.battle_instance = battle
    elif evidence == "registry":
        monkeypatch.setattr(battle_handler, "for_player", lambda _player: battle)
    elif evidence == "index":
        room.db.battles = [81]
    else:
        room.db.battle_81_data = {"retained": True}

    assert not sessions.move_session(player, "north").ok
    assert not sessions.search_session(player).ok
    assert not sessions.leave_session(player).ok
    assert not sessions.room_is_available(room)
    assert session.state == STATE_ACTIVE


@pytest.mark.parametrize("lost_pointers", [False, True])
def test_stale_cleanup_preserves_battle_without_registry(adventure_world, monkeypatch, lost_pointers):
    """Cleanup retains stored battle evidence even after session markers vanish."""
    from world import stale_state

    _hall, room, player = adventure_world
    session = sessions.start_session(player, "alpha_meadow").session
    session.expires_at = sessions._now() - timedelta(minutes=1)
    player.db.battle_id = 81
    player.db.battle_lock = 81
    room.db.battles = [81]
    room.db.battle_81_data = {"original": True}
    room.db.battle_81_encounter = UserDict({
        "source_type": "adventure", "adventure_session_id": session.pk,
    })
    monkeypatch.setattr(stale_state, "resolve_adventure_session", sessions.get_session_by_id)
    if lost_pointers:
        del player.db.adventure_session_id
        del room.db.adventure_session_id

    counts = stale_state.cleanup_stale_state(objects=[player, room], active_battle_ids=set())

    assert not any(counts.values())
    assert player.db.battle_id == player.db.battle_lock == 81
    assert room.db.battles == [81]
    assert room.db.battle_81_data == {"original": True}
    assert session.state == STATE_ACTIVE


def test_pending_receipt_keeps_expired_session_until_original_result_commits(adventure_world, monkeypatch):
    """Expiry cannot discard a receipt; repeated retries record the outcome once."""
    from pokemon.adventures import progress
    from world import stale_state

    _hall, room, player = adventure_world
    session = sessions.start_session(player, "alpha_meadow").session
    sessions.move_session(player, "north")
    sessions.choose_session_route(player, "wild")
    sessions.queue_encounter_result(session.pk, player, "capture")
    session.expires_at = sessions._now() - timedelta(minutes=1)
    monkeypatch.setattr(stale_state, "resolve_adventure_session", sessions.get_session_by_id)

    stale_state.cleanup_stale_state(objects=[player, room], active_battle_ids=set())
    assert player.db.adventure_session_id == room.db.adventure_session_id == session.pk
    assert not sessions.choose_session_route(player, "wild").ok
    committed = []
    monkeypatch.setattr(progress, "record_encounter_result", lambda *args: committed.append(args))
    assert "capture" in sessions.retry_encounter_results(player)
    assert sessions.retry_encounter_results(player).startswith("No Adventure")
    assert len(committed) == 1
    assert session.metadata["encounter_result"] == "capture"
    assert sessions.expire_session(session)
    assert not hasattr(player.db, ADVENTURE_SESSION_ATTR)
    assert not hasattr(room.db, ADVENTURE_SESSION_ATTR)


@pytest.mark.parametrize("action", ["look", "leave", "north"])
def test_player_commands_keep_battle_movement_and_session_intact(adventure_world, action):
    """Inspection stays available and rejected commands do not change cmdsets."""
    _hall, room, player = adventure_world
    session = sessions.start_session(player, "alpha_meadow").session
    player.db.battle_id = 81
    player.cmdset = DummyCmdSet()
    messages = []
    player.msg = messages.append
    command = CmdAdventureNorth() if action == "north" else commands.CmdAdventure()
    command.caller = player
    if action == "north":
        command.func()
    else:
        getattr(command, "_" + action)()

    assert messages
    assert not player.cmdset.added
    assert not player.cmdset.deleted
    assert session.current_node == "entrance"
    assert player.db.adventure_session_id == room.db.adventure_session_id == session.pk


def test_completed_session_pending_cleanup_retains_ownership(adventure_world, monkeypatch):
    """A committed completion still owns its battle until terminal cleanup ends."""
    from pokemon.adventures.constants import STATE_COMPLETED
    from world import stale_state

    _hall, room, player = adventure_world
    session = sessions.start_session(player, "alpha_meadow").session
    session.state = STATE_COMPLETED
    session.completed_at = sessions._now()
    room.db.battles = [81]
    room.db.battle_81_data = {"cleanup_pending": True}
    monkeypatch.setattr(stale_state, "resolve_adventure_session", sessions.get_session_by_id)

    counts = stale_state.cleanup_stale_state(objects=[player, room], active_battle_ids=set())

    assert not any(counts.values())
    assert player.db.adventure_session_id == room.db.adventure_session_id == session.pk
    assert session.state == STATE_COMPLETED


def test_clean_same_route_retry_remains_available(adventure_world):
    """A route reserved before a failed launch can retry without being replaced."""
    _hall, _room, player = adventure_world
    session = sessions.start_session(player, "alpha_meadow").session
    sessions.move_session(player, "north")
    assert sessions.choose_session_route(player, "wild").ok
    assert sessions.choose_session_route(player, "wild").ok
    assert not sessions.choose_session_route(player, "trainer").ok
    assert session.metadata["route_key"] == "wild"


def test_room_storage_handles_evennia_attribute_holder_without_dict():
    """Real attribute holders can return None instead of a Python __dict__."""
    from pokemon.adventures.interlocks import room_battle_ids

    class AttributeHolder:
        """Mirror Evennia's missing-attribute behavior."""

        __slots__ = ()

        def __getattr__(self, name):
            """Return None for an unset persistent attribute."""
            return None

    room = SimpleNamespace(
        db=AttributeHolder(),
        attributes=SimpleNamespace(all=lambda: [SimpleNamespace(key="battle_81_data")]),
    )
    assert room_battle_ids(room) == {81}


def test_unrelated_room_receipt_does_not_protect_stale_battle(adventure_world, monkeypatch):
    """A foreign session ID cannot turn unrelated stale battle data into a lock."""
    from world import stale_state

    _hall, _room, player = adventure_world
    session = sessions.start_session(player, "alpha_meadow").session
    other_room = DummyRoom("Unrelated room")
    other_room.db.battles = [92]
    other_room.db.battle_92_data = {"stale": True}
    other_room.db.battle_92_encounter = {
        "source_type": "adventure", "adventure_session_id": session.pk,
    }
    monkeypatch.setattr(stale_state, "resolve_adventure_session", sessions.get_session_by_id)

    counts = stale_state.cleanup_stale_state(objects=[other_room], active_battle_ids=set())

    assert counts["room_battle_ids"] == 1
    assert other_room.db.battles == []
    assert not hasattr(other_room.db, "battle_92_data")
    assert not hasattr(other_room.db, "battle_92_encounter")
    assert not sessions.room_battle_ids(other_room)
    assert session.state == STATE_ACTIVE


def test_old_session_expiry_preserves_newer_session_pointers(adventure_world):
    """Terminal cleanup never clears a replacement run's player or room marker."""
    _hall, room, player = adventure_world
    session = sessions.start_session(player, "alpha_meadow").session
    player.db.adventure_session_id = room.db.adventure_session_id = session.pk + 1

    assert sessions.expire_session(session)

    assert session.state == STATE_EXPIRED
    assert player.db.adventure_session_id == room.db.adventure_session_id == session.pk + 1


def test_persisted_mapping_receipts_are_scoped_to_original_session(adventure_world):
    """Evennia mapping wrappers preserve receipt identity and terminal state."""
    _hall, room, player = adventure_world
    session = sessions.start_session(player, "alpha_meadow").session
    player.db.pending_adventure_results = UserDict({str(session.pk + 1): "loss"})
    assert not sessions.inspect_adventure_battle(player, session).pending_result
    player.db.pending_adventure_results[str(session.pk)] = "capture"
    assert sessions.inspect_adventure_battle(player, session).pending_result
    player.db.pending_adventure_results = UserDict()
    room.db.battle_81_encounter = UserDict({
        "source_type": "adventure", "adventure_session_id": session.pk,
    })
    room.db.battle_81_battle_result = UserDict({"handled": False, "result": "capture"})
    assert sessions.inspect_adventure_battle(player, session).pending_result

"""Issue #832: persisted battle lifecycle must gate every Adventure action."""

from datetime import timedelta
from types import SimpleNamespace

import pytest

from pokemon.adventures import sessions
from pokemon.adventures.constants import ADVENTURE_SESSION_ATTR, STATE_ACTIVE, STATE_EXPIRED
from tests.test_adventure_sessions import DummyRoom, DummyPlayer, adventure_world, fake_session_model


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

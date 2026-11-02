"""Solo privacy decisions must survive forged and missing volatile identities."""

import contextlib
from types import SimpleNamespace

import pytest

from pokemon.adventures import renderer, sessions
from pokemon.adventures.privacy import PRIVATE_MESSAGE, AdventurePrivacy
from tests.adventure.test_adventure_sessions import (
    DummyPlayer,
    DummyRoom,
    FakeAdventureSession,
    FakeSessionManager,
)


@pytest.fixture
def adventure_world():
    """Provide private room fixtures without cross-module fixture globals."""
    hall = DummyRoom("Adventure Hall", adventure_hall=True)
    room = DummyRoom("Instance", adventure_instance=True)
    hall.exits = [SimpleNamespace(destination=room)]
    player = DummyPlayer()
    player.location = hall
    return hall, room, player


@pytest.fixture(autouse=True)
def isolated_session_model(monkeypatch):
    """Patch this collector's session module, independently of imported fixtures."""
    from pokemon.adventures import progress

    FakeAdventureSession.objects = FakeSessionManager()
    FakeAdventureSession._next_id = 1
    monkeypatch.setattr(sessions, "_session_model", lambda: FakeAdventureSession)
    monkeypatch.setattr(sessions, "_lock_object", lambda _obj: None)
    monkeypatch.setattr(sessions.transaction, "atomic", contextlib.nullcontext)
    monkeypatch.setattr(progress, "safe_finalize_completion", lambda _session: "")


def test_character_identity_is_required_even_on_shared_account(adventure_world):
    """An account relationship and a copied pointer cannot confer ownership."""
    hall, room, owner = adventure_world
    session = sessions.start_session(owner, "alpha_meadow").session
    other = DummyPlayer()
    owner.account = other.account = object()
    other.db.adventure_session_id = session.pk
    assert not AdventurePrivacy.room_access(room, other)
    assert renderer.render_for_room(room, other) == PRIVATE_MESSAGE
    assert AdventurePrivacy.room_access(room, owner)
    assert sessions.get_current_session_for_player(other) is None
    assert room.db.adventure_session_id == session.pk


@pytest.mark.parametrize("problem", ["foreign-leader", "foreign-room", "unknown-session"])
def test_battle_metadata_must_match_canonical_run(adventure_world, problem):
    """A battle's public-looking/cached controller cannot override its run identity."""
    hall, room, owner = adventure_world
    session = sessions.start_session(owner, "alpha_meadow").session
    battle = SimpleNamespace(room=room, encounter_metadata={"source_type": "adventure", "adventure_session_id": session.pk})
    assert AdventurePrivacy.battle_access(battle, owner)
    if problem == "foreign-leader":
        viewer = DummyPlayer()
        battle.captainA = viewer
    else:
        viewer = owner
        if problem == "foreign-room":
            battle.room = hall
        else:
            battle.encounter_metadata["adventure_session_id"] = session.pk + 1
    assert not AdventurePrivacy.battle_access(battle, viewer)


def test_unreserved_instances_and_ordinary_battles(adventure_world):
    """Idle private rooms deny entry; ordinary battles retain their public policy."""
    hall, room, player = adventure_world
    assert not AdventurePrivacy.room_access(room, player)
    assert AdventurePrivacy.room_access(hall, player)
    assert AdventurePrivacy.battle_access(SimpleNamespace(room=hall, encounter_metadata={}), player)


@pytest.mark.parametrize("flag", [True, 1, 2, "True", "yes", "1", "on"])
def test_existing_truthy_room_flags_remain_private(adventure_world, flag):
    """Admission must recognize every legacy flag accepted by room allocation."""
    _hall, room, player = adventure_world
    room.db.adventure_instance = flag
    assert not AdventurePrivacy.room_access(room, player)
    assert renderer.render_for_room(room, player) == PRIVATE_MESSAGE


@pytest.mark.parametrize("path", ["room", "battle"])
@pytest.mark.parametrize("unreadable_tag", [False, True])
def test_unavailable_ownership_storage_denies_without_raising(adventure_world, monkeypatch, path, unreadable_tag):
    """A privacy lookup outage cannot leak output or interrupt result cleanup."""
    _hall, room, player = adventure_world
    session = sessions.start_session(player, "alpha_meadow").session

    def unavailable():
        raise RuntimeError("fixture ownership storage unavailable")

    monkeypatch.setattr(sessions, "_session_model", unavailable)
    if unreadable_tag:
        class UnavailableAttributes:
            """A cold Evennia attribute cache also needs database availability."""

            def __getattr__(self, key):
                raise RuntimeError("fixture room attribute storage unavailable")

        room.db = UnavailableAttributes()
    if path == "room":
        assert not AdventurePrivacy.room_access(room, player)
    else:
        battle = SimpleNamespace(room=room, encounter_metadata={"source_type": "adventure", "adventure_session_id": session.pk})
        assert not AdventurePrivacy.battle_access(battle, player)


def test_completed_owner_survives_marker_loss(adventure_world):
    """Completion remains an occupancy claim until the original owner leaves."""
    hall, room, owner = adventure_world
    session = sessions.start_session(owner, "alpha_meadow").session
    session.state = "completed"
    del owner.db.adventure_session_id
    del room.db.adventure_session_id
    assert sessions.get_current_session_for_player(owner) is session
    assert not sessions.room_is_available(room)
    assert sessions.leave_session(owner).ok
    assert sessions.room_is_available(room)
    assert not AdventurePrivacy.room_access(room, owner)

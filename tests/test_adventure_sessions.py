import types

import pytest

from pokemon.adventures import sessions
from pokemon.adventures.constants import (
    ADVENTURE_SESSION_ATTR,
    STATE_ABANDONED,
    STATE_COMPLETED,
)


class DummyDB(types.SimpleNamespace):
    pass


class DummyRoom:
    _next_id = 1

    def __init__(self, key, **attrs):
        self.id = DummyRoom._next_id
        DummyRoom._next_id += 1
        self.key = key
        self.db = DummyDB(**attrs)
        self.ndb = DummyDB()
        self.exits = []

    def contents_get(self, content_type=None):
        return self.exits if content_type == "exit" else []


class DummyPlayer:
    _next_id = 100

    def __init__(self, key="Player"):
        self.id = DummyPlayer._next_id
        DummyPlayer._next_id += 1
        self.key = key
        self.db = DummyDB()
        self.ndb = DummyDB()
        self.location = None
        self.moves = []

    def move_to(self, destination, quiet=False):
        self.moves.append((destination, quiet))
        self.location = destination
        return True


class FakeQuerySet:
    def __init__(self, items):
        self.items = list(items)

    def first(self):
        return self.items[0] if self.items else None


class FakeSessionManager:
    def __init__(self):
        self.store = {}

    def create(self, **kwargs):
        session = FakeAdventureSession(**kwargs)
        self.store[session.pk] = session
        return session

    def filter(self, **kwargs):
        items = list(self.store.values())
        for key, value in kwargs.items():
            attr = "pk" if key == "pk" else key
            items = [item for item in items if getattr(item, attr) == value]
        return FakeQuerySet(items)


class FakeAdventureSession:
    objects = FakeSessionManager()
    _next_id = 1

    def __init__(self, **kwargs):
        self.pk = FakeAdventureSession._next_id
        self.id = self.pk
        FakeAdventureSession._next_id += 1
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.completed_at = kwargs.get("completed_at")
        self.saved_fields = []

    @property
    def leader_id(self):
        return getattr(self.leader, "id", None)

    @property
    def instance_room_id(self):
        return getattr(self.instance_room, "id", None)

    @property
    def return_location_id(self):
        return getattr(self.return_location, "id", None)

    def save(self, update_fields=None):
        self.saved_fields.append(update_fields)
        self.__class__.objects.store[self.pk] = self


@pytest.fixture(autouse=True)
def fake_session_model(monkeypatch):
    FakeAdventureSession.objects = FakeSessionManager()
    FakeAdventureSession._next_id = 1
    monkeypatch.setattr(sessions, "_session_model", lambda: FakeAdventureSession)
    return FakeAdventureSession.objects


@pytest.fixture
def adventure_world():
    hall = DummyRoom("Adventure Hall", adventure_hall=True)
    instance = DummyRoom("Adventure Instance Room #1", adventure_instance=True)
    hall.exits = [types.SimpleNamespace(destination=instance)]
    player = DummyPlayer()
    player.location = hall
    return hall, instance, player


def test_start_session_reserves_instance_room_and_moves_player(adventure_world):
    hall, instance, player = adventure_world

    result = sessions.start_session(player, "alpha_meadow")

    assert result.ok
    assert result.session.template_key == "alpha_meadow"
    assert player.location is instance
    assert getattr(player.db, ADVENTURE_SESSION_ATTR) == result.session.pk
    assert getattr(instance.db, ADVENTURE_SESSION_ATTR) == result.session.pk
    assert result.session.return_location is hall
    assert result.session.current_node == "entrance"


def test_start_requires_adventure_hall(adventure_world):
    _hall, _instance, player = adventure_world
    player.location = DummyRoom("Normal Room")

    result = sessions.start_session(player, "alpha_meadow")

    assert not result.ok
    assert result.message == "You need to start adventures from the Adventure Hall."


def test_movement_search_and_return_complete_objectives(adventure_world):
    _hall, _instance, player = adventure_world
    start = sessions.start_session(player, "alpha_meadow")
    session = start.session

    assert sessions.move_session(player, "north").ok
    result = sessions.move_session(player, "north")
    assert result.ok
    assert session.current_node == "old_tree"
    assert session.objective_progress["reach_old_tree"] == 1

    result = sessions.search_session(player)
    assert result.ok
    assert "fresh tracks" in result.message
    assert session.objective_progress["search_old_tree"] == 1

    sessions.move_session(player, "south")
    result = sessions.move_session(player, "south")

    assert result.ok
    assert session.current_node == "entrance"
    assert session.objective_progress["return_entrance"] == 1
    assert session.state == STATE_COMPLETED
    assert "Adventure complete" in result.message


def test_invalid_virtual_movement_does_not_change_node(adventure_world):
    _hall, _instance, player = adventure_world
    session = sessions.start_session(player, "alpha_meadow").session

    result = sessions.move_session(player, "west")

    assert not result.ok
    assert result.message == "You can't go that way."
    assert session.current_node == "entrance"


def test_leave_completed_session_cleans_attrs_and_returns_player(adventure_world):
    hall, instance, player = adventure_world
    session = sessions.start_session(player, "alpha_meadow").session
    sessions.move_session(player, "north")
    sessions.move_session(player, "north")
    sessions.search_session(player)
    sessions.move_session(player, "south")
    sessions.move_session(player, "south")

    result = sessions.leave_session(player)

    assert result.ok
    assert "complete Alpha Meadow Survey" in result.message
    assert player.location is hall
    assert not hasattr(player.db, ADVENTURE_SESSION_ATTR)
    assert not hasattr(instance.db, ADVENTURE_SESSION_ATTR)
    assert session.state == STATE_COMPLETED


def test_leave_unfinished_session_marks_abandoned(adventure_world):
    hall, instance, player = adventure_world
    session = sessions.start_session(player, "alpha_meadow").session

    result = sessions.leave_session(player)

    assert result.ok
    assert player.location is hall
    assert not hasattr(player.db, ADVENTURE_SESSION_ATTR)
    assert not hasattr(instance.db, ADVENTURE_SESSION_ATTR)
    assert session.state == STATE_ABANDONED


def test_room_lookup_recovers_active_session(adventure_world):
    _hall, instance, player = adventure_world
    session = sessions.start_session(player, "alpha_meadow").session

    recovered = sessions.get_active_session_for_room(instance, player)

    assert recovered is session


def test_sync_player_to_active_session_moves_missing_location(adventure_world):
    _hall, instance, player = adventure_world
    session = sessions.start_session(player, "alpha_meadow").session
    player.location = None

    recovered = sessions.sync_player_to_active_session(player)

    assert recovered is session
    assert player.location is instance


def test_sync_player_to_active_session_restores_marker_and_wrong_location(adventure_world):
    _hall, instance, player = adventure_world
    session = sessions.start_session(player, "alpha_meadow").session
    delattr(instance.db, ADVENTURE_SESSION_ATTR)
    player.location = DummyRoom("Elsewhere")

    recovered = sessions.sync_player_to_active_session(player)

    assert recovered is session
    assert getattr(instance.db, ADVENTURE_SESSION_ATTR) == session.pk
    assert player.location is instance

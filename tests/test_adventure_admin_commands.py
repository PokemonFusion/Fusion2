import types
from datetime import timedelta

import pytest

from commands.admin import cmd_adventureadmin as admin
from pokemon.adventures import sessions
from pokemon.adventures.constants import ADVENTURE_SESSION_ATTR, STATE_ABANDONED, STATE_ACTIVE, STATE_COMPLETED


class DummyDB(types.SimpleNamespace):
    pass


class DummyCmdSet:
    def __init__(self):
        self.deleted = []

    def delete(self, cmdset):
        self.deleted.append(cmdset)


class DummyRoom:
    _next_id = 1

    def __init__(self, key, **attrs):
        self.id = DummyRoom._next_id
        DummyRoom._next_id += 1
        self.key = key
        self.db = DummyDB(**attrs)


class DummyPlayer:
    _next_id = 100

    def __init__(self, key="Player"):
        self.id = DummyPlayer._next_id
        DummyPlayer._next_id += 1
        self.key = key
        self.db = DummyDB()
        self.cmdset = DummyCmdSet()
        self.location = None
        self.moves = []

    def move_to(self, destination, quiet=False):
        self.moves.append((destination, quiet))
        self.location = destination
        return True


class DummyCaller(DummyPlayer):
    def __init__(self, registry=None):
        super().__init__("Staff")
        self.messages = []
        self.registry = registry or {}

    def msg(self, text):
        self.messages.append(text)

    def search(self, query, global_search=False):
        return self.registry.get(query)


class FakeQuerySet(list):
    def first(self):
        return self[0] if self else None


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

    def save(self, update_fields=None):
        self.saved_fields.append(update_fields)
        self.__class__.objects.store[self.pk] = self


@pytest.fixture(autouse=True)
def fake_session_model(monkeypatch):
    FakeAdventureSession.objects = FakeSessionManager()
    FakeAdventureSession._next_id = 1
    DummyRoom._next_id = 1
    DummyPlayer._next_id = 100
    monkeypatch.setattr(sessions, "_session_model", lambda: FakeAdventureSession)
    return FakeAdventureSession.objects


def _world(player_key="Player"):
    hall = DummyRoom("Adventure Hall", adventure_hall=True)
    instance = DummyRoom("Adventure Instance Room #1", adventure_instance=True)
    player = DummyPlayer(player_key)
    player.location = instance
    return hall, instance, player


def _make_session(player, instance, hall, state=STATE_ACTIVE, with_pointers=True):
    now = sessions._now()
    session = FakeAdventureSession.objects.create(
        template_key="alpha_meadow",
        state=state,
        leader=player,
        instance_room=instance,
        return_location=hall,
        current_node="entrance",
        visited_nodes=["entrance"],
        objective_progress={"reach_old_tree": 0},
        started_at=now - timedelta(minutes=5),
        expires_at=now + timedelta(minutes=55),
        metadata={},
    )
    if with_pointers:
        player.db.adventure_session_id = session.pk
        instance.db.adventure_session_id = session.pk
    return session


def _run_admin(switches, args="", caller=None):
    caller = caller or DummyCaller()
    cmd = admin.CmdAdventureAdmin()
    cmd.caller = caller
    cmd.args = args
    cmd.cmdstring = "+adventureadmin"
    cmd.switches = set(switches)
    cmd.func()
    return caller


def test_adventure_admin_command_is_staff_locked():
    assert admin.CmdAdventureAdmin.locks == "cmd:perm(Wizards)"
    assert "+advadmin" in admin.CmdAdventureAdmin.aliases


def test_adventure_admin_list_shows_active_and_completed_not_left():
    hall, instance, player = _world("ActivePlayer")
    active = _make_session(player, instance, hall, STATE_ACTIVE)
    hall2, instance2, player2 = _world("CompletePlayer")
    completed = _make_session(player2, instance2, hall2, STATE_COMPLETED)
    hall3, instance3, player3 = _world("HistoricalPlayer")
    historical = _make_session(player3, instance3, hall3, STATE_COMPLETED, with_pointers=False)

    caller = _run_admin({"list"})
    output = caller.messages[-1]

    assert f"#{active.pk}" in output
    assert "state=active" in output
    assert f"#{completed.pk}" in output
    assert "state=completed" in output
    assert f"#{historical.pk}" not in output


def test_adventure_admin_info_reports_pointer_status():
    hall, instance, player = _world()
    session = _make_session(player, instance, hall)

    caller = _run_admin({"info"}, str(session.pk))
    output = caller.messages[-1]

    assert f"Adventure session #{session.pk}" in output
    assert "Player pointer: 1 (matches: yes)" in output
    assert "Room pointer: 1 (matches: yes)" in output
    assert "Pointers match: yes" in output
    assert "Objective progress: reach_old_tree=0" in output


def test_adventure_admin_abort_active_session_abandons_and_clears():
    hall, instance, player = _world()
    session = _make_session(player, instance, hall)

    caller = _run_admin({"abort"}, str(session.pk))

    assert "session abandoned" in caller.messages[-1]
    assert session.state == STATE_ABANDONED
    assert not hasattr(player.db, ADVENTURE_SESSION_ATTR)
    assert not hasattr(instance.db, ADVENTURE_SESSION_ATTR)
    assert player.location is hall
    assert player.cmdset.deleted


def test_adventure_admin_abort_completed_session_does_not_abandon():
    hall, instance, player = _world()
    session = _make_session(player, instance, hall, STATE_COMPLETED)

    caller = _run_admin({"abort"}, str(session.pk))

    assert "completed session cleaned up" in caller.messages[-1]
    assert session.state == STATE_COMPLETED
    assert not hasattr(player.db, ADVENTURE_SESSION_ATTR)
    assert not hasattr(instance.db, ADVENTURE_SESSION_ATTR)
    assert player.location is hall


def test_adventure_admin_return_player_uses_current_session():
    hall, instance, player = _world()
    session = _make_session(player, instance, hall)
    caller = DummyCaller(registry={"Player": player})

    _run_admin({"return"}, "Player", caller=caller)

    assert f"Returned Player #100 from Adventure session #{session.pk}." in caller.messages[-1]
    assert session.state == STATE_ABANDONED
    assert player.location is hall
    assert not hasattr(player.db, ADVENTURE_SESSION_ATTR)
    assert not hasattr(instance.db, ADVENTURE_SESSION_ATTR)


def test_adventure_admin_cleanup_uses_stale_state(monkeypatch):
    monkeypatch.setattr(admin, "cleanup_stale_state", lambda: {"adventure_attrs": 2})
    monkeypatch.setattr(admin, "format_cleanup_counts", lambda counts: "cleared adventure_attrs=2")

    caller = _run_admin({"cleanup"})

    assert caller.messages[-1] == "Adventure cleanup ran: cleared adventure_attrs=2"


def test_adventure_admin_validate_all_reports_ok():
    caller = _run_admin({"validate"}, "all")

    assert "Adventure template validation:" in caller.messages[-1]
    assert "alpha_meadow: OK" in caller.messages[-1]


def test_adventure_admin_preview_node_renders_without_session():
    caller = _run_admin({"preview"}, "alpha_meadow old_tree")
    output = caller.messages[-1]

    assert "Alpha Meadow Survey" in output
    assert "Old Tree" in output
    assert "Exits: south" in output

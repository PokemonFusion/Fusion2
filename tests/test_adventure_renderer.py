import types

from pokemon.adventures import renderer, sessions


class DummyDB(types.SimpleNamespace):
    pass


class DummyRoom:
    _next_id = 500

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
    _next_id = 800

    def __init__(self):
        self.id = DummyPlayer._next_id
        DummyPlayer._next_id += 1
        self.key = "Player"
        self.db = DummyDB()
        self.ndb = DummyDB()
        self.location = None

    def move_to(self, destination, quiet=False):
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

    @property
    def leader_id(self):
        return getattr(self.leader, "id", None)

    @property
    def instance_room_id(self):
        return getattr(self.instance_room, "id", None)

    def save(self, update_fields=None):
        self.__class__.objects.store[self.pk] = self


def test_render_session_shows_location_map_exits_and_objectives(monkeypatch):
    FakeAdventureSession.objects = FakeSessionManager()
    FakeAdventureSession._next_id = 1
    hall = DummyRoom("Adventure Hall", adventure_hall=True)
    instance = DummyRoom("Adventure Instance Room #1", adventure_instance=True)
    hall.exits = [type("Exit", (), {"destination": instance})()]
    player = DummyPlayer()
    player.location = hall
    monkeypatch.setattr(sessions, "_session_model", lambda: FakeAdventureSession)
    session = sessions.start_session(player, "alpha_meadow").session
    sessions.move_session(player, "north")

    text = renderer.render_session(session)

    assert "Alpha Meadow Survey" in text
    assert "Tall Grass Path" in text
    assert "Map:" in text
    assert "Exits: east, north, south" in text
    assert "[ ] Reach the Old Tree." in text


def test_render_for_room_uses_matching_active_session(monkeypatch):
    FakeAdventureSession.objects = FakeSessionManager()
    FakeAdventureSession._next_id = 1
    hall = DummyRoom("Adventure Hall", adventure_hall=True)
    instance = DummyRoom("Adventure Instance Room #1", adventure_instance=True)
    hall.exits = [type("Exit", (), {"destination": instance})()]
    player = DummyPlayer()
    player.location = hall
    monkeypatch.setattr(sessions, "_session_model", lambda: FakeAdventureSession)
    sessions.start_session(player, "alpha_meadow")

    text = renderer.render_for_room(instance, player)

    assert text is not None
    assert "Meadow Entrance" in text

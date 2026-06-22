"""Tests for room editor views and AJAX behavior."""
import json
import sys
import types

import django
import pytest
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory

# Configure minimal Django settings.
if not settings.configured:
    settings.configure(
        SECRET_KEY="test",
        DEFAULT_CHARSET="utf-8",
        INSTALLED_APPS=[],
        USE_I18N=False,
        ROOT_URLCONF="roomeditor.urls",
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [],
                "APP_DIRS": True,
                "OPTIONS": {},
            }
        ],
        CHANNEL_LOG_NUM_TAIL_LINES=100,
    )
    django.setup()

# Stub evennia modules before importing views.
fake_evennia = types.ModuleType("evennia")
fake_evennia.DefaultExit = types.SimpleNamespace(path="evennia.default_exit")
fake_models = types.ModuleType("evennia.objects.models")
fake_models.ObjectDB = type("ObjectDB", (), {})
fake_objects = types.ModuleType("evennia.objects")
fake_utils = types.ModuleType("evennia.utils")
fake_create = types.ModuleType("evennia.utils.create")
fake_create.create_object = lambda **kwargs: None
fake_utils.create = fake_create
sys.modules.setdefault("evennia", fake_evennia)
sys.modules.setdefault("evennia.objects", fake_objects)
sys.modules.setdefault("evennia.objects.models", fake_models)
sys.modules.setdefault("evennia.utils", fake_utils)
sys.modules.setdefault("evennia.utils.create", fake_create)

from roomeditor import views
from roomeditor.auth import has_builder_access
from roomeditor.views import locks


class DummyAliases:
    """Simple alias container."""

    def __init__(self):
        self.aliases = []

    def add(self, val):
        self.aliases.append(val)

    def clear(self):
        self.aliases.clear()

    def all(self):
        return list(self.aliases)


class DummyLock:
    def __init__(self, lockstring):
        self.lockstring = lockstring


class DummyLocks:
    """Minimal lock handler."""

    def __init__(self):
        self.locks = []

    def add(self, lockstring):
        self.locks.append(DummyLock(lockstring))

    def clear(self):
        self.locks.clear()

    def first(self):
        return self.locks[0] if self.locks else None

    def all(self):
        return list(self.locks)


class DummyExit:
    """Stand-in for Evennia exits."""

    _counter = 1

    def __init__(self, db_key, db_location, db_destination, typeclass_path="", db_typeclass_path="", **kwargs):
        self.id = DummyExit._counter
        DummyExit._counter += 1
        self.key = db_key
        self.db_key = db_key
        self.typeclass_path = typeclass_path or db_typeclass_path
        self.db_location = db_location
        self.location = db_location
        self.destination = db_destination
        self.db_destination = db_destination
        self.db_location_id = getattr(db_location, "id", db_location)
        self.db_destination_id = getattr(db_destination, "id", db_destination)
        self.destination_id = getattr(db_destination, "id", db_destination)
        self.aliases = DummyAliases()
        self.locks = DummyLocks()
        self.db = types.SimpleNamespace(desc="", err_traverse="")
        self.home = kwargs.get("home")
        self.cmdset_terms = set()
        self.at_cmdset_get_calls = []

    def save(self):
        pass

    def delete(self):
        pass

    def at_cmdset_get(self, **kwargs):
        self.at_cmdset_get_calls.append(kwargs)
        self.cmdset_terms = {self.key.lower(), *(alias.lower() for alias in self.aliases.all())}

    def command_works(self, raw):
        return raw.lower() in self.cmdset_terms


class DummyRoom:
    def __init__(self, pk, key="Room"):
        self.id = pk
        self.pk = pk
        self.key = key
        self.db_key = key
        self.typeclass_path = "typeclasses.rooms.Room"
        self.db = types.SimpleNamespace(desc="")
        self.locks = DummyLocks()
        self.location = None
        self.home = None
        self.deleted = False

    def delete(self):
        self.deleted = True


class DummyUser:
    def __init__(self, *, authenticated=True, builder=True, superuser=False):
        self.id = 99
        self.is_authenticated = authenticated
        self.is_superuser = superuser
        self.builder = builder

    def check_permstring(self, permission):
        return self.builder and permission in {"Builder", "Builders"}


def attach_user(request, user=None):
    request.user = user or DummyUser()
    return request


class RoomQuery(list):
    def order_by(self, attr):
        return RoomQuery(sorted(self, key=lambda x: getattr(x, attr.replace("db_", ""))))

    def filter(self, **kwargs):
        results = []
        for room in self:
            match = True
            for key, value in kwargs.items():
                if key == "db_key__icontains":
                    match = str(value).lower() in room.db_key.lower()
                elif getattr(room, key.replace("db_", ""), None) != value:
                    match = False
                if not match:
                    break
            if match:
                results.append(room)
        return RoomQuery(results)


class ExitQuery(list):
    def exists(self):
        return bool(self)

    def order_by(self, attr):
        return sorted(self, key=lambda x: getattr(x, attr))


class ExitManager:
    def __init__(self, store):
        self.store = store

    def filter(self, **kwargs):
        results = []
        for ex in self.store.values():
            match = True
            for k, v in kwargs.items():
                if k in {"db_location", "location"}:
                    actual = ex.db_location
                elif k in {"db_destination", "destination"}:
                    actual = ex.db_destination
                elif k in {"db_location_id", "location_id"}:
                    actual = ex.db_location_id
                elif k in {"db_destination_id", "destination_id"}:
                    actual = ex.db_destination_id
                else:
                    actual = getattr(ex, k.replace("db_", ""))
                if actual != v:
                    match = False
                    break
            if match:
                results.append(ex)
        return ExitQuery(results)

    def values_list(self, attr, flat=False):
        if attr == "db_destination_id":
            return [ex.db_destination_id for ex in self.store.values()]
        return [getattr(ex, attr.replace("db_", "")) for ex in self.store.values()]


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def dummy_env(monkeypatch):
    """Set up a fake environment with in-memory objects."""

    room_store = {1: DummyRoom(1, "R1"), 2: DummyRoom(2, "R2")}
    exit_store = {}
    DummyExit._counter = 1
    create_calls = []

    def create_exit(**kwargs):
        ex = DummyExit(**kwargs)
        def _del():
            del exit_store[ex.id]
        ex.delete = _del
        exit_store[ex.id] = ex
        return ex

    def create_room(**kwargs):
        pk = max(room_store) + 1
        room = DummyRoom(pk, kwargs.get("db_key", "Room"))
        room.db_location = kwargs.get("db_location")
        room.location = kwargs.get("db_location")
        room.home = kwargs.get("home")
        room.db_lock_storage = kwargs.get("db_lock_storage", "")
        room.typeclass_path = kwargs.get("typeclass_path") or kwargs.get("db_typeclass_path") or room.typeclass_path
        def _del():
            del room_store[room.id]
        room.delete = _del
        room_store[room.id] = room
        return room

    class DummyObjectDB:
        class Manager:
            def create(self, **kwargs):
                if "db_destination" in kwargs:
                    return create_exit(**kwargs)
                return create_room(**kwargs)

        objects = Manager()

    def fake_create_object(
        *,
        typeclass=None,
        key=None,
        location=None,
        home=None,
        aliases=None,
        locks=None,
        destination=None,
        attributes=None,
        **kwargs,
    ):
        create_calls.append(
            {
                "typeclass": typeclass,
                "key": key,
                "location": location,
                "home": home,
                "aliases": aliases,
                "locks": locks,
                "destination": destination,
                "attributes": attributes,
            }
        )
        if destination is not None:
            obj = create_exit(
                db_key=key,
                db_location=location,
                db_destination=destination,
                db_typeclass_path=typeclass,
                home=home,
            )
        else:
            obj = create_room(
                db_key=key,
                db_location=location,
                db_typeclass_path=typeclass,
                home=home,
            )
        for alias in aliases or []:
            obj.aliases.add(alias)
        if locks:
            obj.locks.add(locks)
        for key, value, *_rest in attributes or []:
            setattr(obj.db, key, value)
        return obj

    room_manager = RoomQuery(room_store.values())
    exit_manager = ExitManager(exit_store)

    def fake_get_object_or_404(qs, pk):
        if qs is room_manager:
            return room_store[pk]
        if qs is exit_manager:
            return exit_store[pk]
        raise KeyError

    class DummyExitForm:
        def __init__(self, data=None):
            data = data or {}
            self.cleaned_data = {
                "key": data.get("key"),
                "destination": room_store[int(data.get("destination", 2))],
                "description": data.get("description", ""),
                "lockstring": data.get("lockstring", ""),
                "err_msg": data.get("err_msg", ""),
                "aliases": data.get("aliases", ""),
                "auto_reverse": data.get("auto_reverse") in ("on", "true", "1", True),
            }

        def is_valid(self):
            return True

        def cleaned_alias_list(self):
            return [a.strip() for a in self.cleaned_data["aliases"].split(",") if a.strip()]

    class DummyRoomForm:
        def __init__(self, data=None, instance=None):
            self.data = data or {}
            self.instance = instance

        def is_valid(self):
            return True

        def save(self):
            self.instance.key = self.data.get("db_key", self.instance.key)
            self.instance.db.desc = self.data.get("db_desc", self.instance.db.desc)

    captured = {"template": None, "context": None, "create_calls": create_calls}

    def fake_render(request, template, context):
        captured["template"] = template
        captured["context"] = context
        if template == "roomeditor/_exit_row.html":
            return HttpResponse(f"ROW:{context['ex'].key}")
        if template == "roomeditor/_room_row.html":
            return HttpResponse(f"ROOM:{context['room'].key}")
        return HttpResponse("FORM")

    monkeypatch.setattr(views, "_room_qs", lambda: room_manager)
    monkeypatch.setattr(views, "_exit_qs", lambda: exit_manager)
    monkeypatch.setattr(views, "get_object_or_404", fake_get_object_or_404)
    monkeypatch.setattr(views, "ObjectDB", DummyObjectDB)
    monkeypatch.setattr(views, "create_object", fake_create_object)
    monkeypatch.setattr(views, "ExitForm", DummyExitForm)
    monkeypatch.setattr(views, "RoomForm", DummyRoomForm)
    monkeypatch.setattr(views, "render", fake_render)

    class DummyAtomic:
        def __enter__(self):
            return None

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(views, "transaction", types.SimpleNamespace(atomic=lambda: DummyAtomic()))
    return room_store, exit_store, captured


def test_ansi_preview_returns_html(rf, monkeypatch):
    """ansi_preview should return rendered HTML."""

    monkeypatch.setattr(views, "parse_html", lambda text, strip_ansi=False: f"<p>{text}</p>")
    request = attach_user(rf.post("/ansi/preview/", {"text": "|rred|n"}))
    resp = views.ansi_preview(request)
    assert json.loads(resp.content) == {"html": "<p>|rred|n</p>"}


def test_exit_new_get_and_ajax_create(rf, dummy_env):
    """exit_new renders form and creates exits via AJAX."""

    room_store, exit_store, captured = dummy_env
    request = attach_user(rf.get("/exit/new/1/"))
    views.exit_new(request, room_pk=1)
    assert captured["template"] == "roomeditor/_exit_form.html"

    request = attach_user(rf.post(
        "/exit/new/1/",
        {"key": "north", "destination": "2"},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    ))
    resp = views.exit_new(request, room_pk=1)
    assert captured["template"] == "roomeditor/_exit_row.html"
    data = json.loads(resp.content)
    assert data["ok"] is True
    assert data["row_html"] == "ROW:north"
    assert any(ex.key == "north" for ex in exit_store.values())
    assert any(ex.typeclass_path == "typeclasses.exits.Exit" for ex in exit_store.values())
    call = captured["create_calls"][-1]
    assert call["typeclass"] == "typeclasses.exits.Exit"
    assert call["key"] == "north"
    assert call["location"] is room_store[1]
    assert call["home"] is room_store[1]
    assert call["destination"] is room_store[2]


def test_exit_new_auto_reverse_uses_safe_create(rf, dummy_env):
    """exit_new gives generated reverse aliases, not forward aliases."""

    room_store, exit_store, captured = dummy_env
    request = attach_user(rf.post(
        "/exit/new/1/",
        {"key": "north", "destination": "2", "aliases": "n", "auto_reverse": "on"},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    ))
    resp = views.exit_new(request, room_pk=1)
    assert json.loads(resp.content)["ok"] is True
    assert [call["key"] for call in captured["create_calls"]] == ["north", "south"]
    forward_call = captured["create_calls"][0]
    reverse_call = captured["create_calls"][-1]
    assert forward_call["aliases"] == ["n"]
    assert reverse_call["location"] is room_store[2]
    assert reverse_call["home"] is room_store[2]
    assert reverse_call["destination"] is room_store[1]
    assert reverse_call["aliases"] == ["s"]
    reverse_exit = next(ex for ex in exit_store.values() if ex.key == "south")
    assert reverse_exit.aliases.all() == ["s"]
    assert "n" not in reverse_exit.aliases.all()
    assert len(exit_store) == 2


def test_exit_new_reverse_alias_conflict_blocks_both_exits(rf, dummy_env):
    """A generated reverse alias conflict aborts before creating either new exit."""

    room_store, exit_store, captured = dummy_env
    existing = views.create_object(
        typeclass="typeclasses.exits.Exit",
        key="east",
        location=room_store[2],
        home=room_store[2],
        destination=room_store[1],
        aliases=["s"],
    )
    create_count = len(captured["create_calls"])

    request = attach_user(rf.post(
        "/exit/new/1/",
        {"key": "north", "destination": "2", "aliases": "n", "auto_reverse": "on"},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    ))
    resp = views.exit_new(request, room_pk=1)
    assert resp.status_code == 400
    data = json.loads(resp.content)
    assert data["ok"] is False
    assert "already exists" in data["error"]
    assert f"#{existing.id}" in data["error"]
    assert len(captured["create_calls"]) == create_count
    assert len(exit_store) == 1
    assert all(ex.key != "north" for ex in exit_store.values())
    assert all(ex.key != "south" for ex in exit_store.values())


def test_exit_new_reverse_key_conflict_blocks_both_exits(rf, dummy_env):
    """A reverse key conflict aborts before creating either new exit."""

    room_store, exit_store, captured = dummy_env
    existing = views.create_object(
        typeclass="typeclasses.exits.Exit",
        key="south",
        location=room_store[2],
        home=room_store[2],
        destination=room_store[1],
    )
    create_count = len(captured["create_calls"])

    request = attach_user(rf.post(
        "/exit/new/1/",
        {"key": "north", "destination": "2", "aliases": "n", "auto_reverse": "on"},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    ))
    resp = views.exit_new(request, room_pk=1)
    assert resp.status_code == 400
    data = json.loads(resp.content)
    assert data["ok"] is False
    assert "already exists" in data["error"]
    assert f"#{existing.id}" in data["error"]
    assert len(captured["create_calls"]) == create_count
    assert len(exit_store) == 1
    assert all(ex.key != "north" for ex in exit_store.values())


def test_exit_new_rejects_duplicate_key_or_alias(rf, dummy_env):
    """exit_new rejects duplicate exit command terms in the source room."""

    room_store, exit_store, _ = dummy_env
    existing = views.create_object(
        typeclass="typeclasses.exits.Exit",
        key="north",
        location=room_store[1],
        home=room_store[1],
        destination=room_store[2],
        aliases=["n"],
    )
    request = attach_user(rf.post(
        "/exit/new/1/",
        {"key": "east", "destination": "2", "aliases": "n"},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    ))
    resp = views.exit_new(request, room_pk=1)
    assert resp.status_code == 400
    data = json.loads(resp.content)
    assert data["ok"] is False
    assert "already exists" in data["error"]
    assert f"#{existing.id}" in data["error"]


def test_exit_edit_ajax_updates_exit(rf, dummy_env):
    """exit_edit updates an existing exit and returns new row HTML."""

    room_store, exit_store, captured = dummy_env
    ex = views.ObjectDB.objects.create(
        typeclass_path="", db_key="north", db_location=room_store[1], db_destination=room_store[2]
    )
    request = attach_user(rf.post(
        f"/exit/{ex.id}/edit/",
        {
            "key": "east",
            "destination": "2",
            "description": "desc",
            "lockstring": "lock",
            "err_msg": "err",
            "aliases": "a,b",
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    ))
    resp = views.exit_edit(request, pk=ex.id)
    assert captured["template"] == "roomeditor/_exit_row.html"
    data = json.loads(resp.content)
    assert data["row_html"] == "ROW:east"
    ex = exit_store[ex.id]
    assert ex.key == "east"
    assert ex.db.desc == "desc"
    assert ex.db.err_traverse == "err"
    assert ex.aliases.all() == ["a", "b"]
    assert ex.locks.first().lockstring == "lock"
    assert ex.at_cmdset_get_calls[-1] == {"force_init": True}


def test_exit_edit_refreshes_cmdset_terms_without_reload(rf, dummy_env):
    """exit_edit rebuilds ExitCmdSet so old commands stop and new commands work."""

    room_store, exit_store, _ = dummy_env
    ex = views.create_object(
        typeclass="typeclasses.exits.Exit",
        key="north",
        location=room_store[1],
        home=room_store[1],
        destination=room_store[2],
        aliases=["n"],
    )
    ex.at_cmdset_get(force_init=True)
    assert ex.command_works("north") is True
    assert ex.command_works("n") is True
    assert ex.command_works("east") is False

    request = attach_user(rf.post(
        f"/exit/{ex.id}/edit/",
        {
            "key": "east",
            "destination": "2",
            "aliases": "e",
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    ))
    resp = views.exit_edit(request, pk=ex.id)
    assert json.loads(resp.content)["ok"] is True
    assert ex.command_works("north") is False
    assert ex.command_works("n") is False
    assert ex.command_works("east") is True
    assert ex.command_works("e") is True
    assert ex.at_cmdset_get_calls[-1] == {"force_init": True}


def test_exit_edit_rejects_duplicate_key_or_alias(rf, dummy_env):
    """exit_edit rejects command terms already used by another exit in the room."""

    room_store, exit_store, _ = dummy_env
    views.create_object(
        typeclass="typeclasses.exits.Exit",
        key="north",
        location=room_store[1],
        home=room_store[1],
        destination=room_store[2],
        aliases=["n"],
    )
    ex = views.create_object(
        typeclass="typeclasses.exits.Exit",
        key="east",
        location=room_store[1],
        home=room_store[1],
        destination=room_store[2],
    )
    request = attach_user(rf.post(
        f"/exit/{ex.id}/edit/",
        {"key": "south", "destination": "2", "aliases": "n"},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    ))
    resp = views.exit_edit(request, pk=ex.id)
    assert resp.status_code == 400
    assert "already exists" in json.loads(resp.content)["error"]


def test_exit_edit_non_ajax_redirects_to_exit_location(rf, dummy_env, monkeypatch):
    """exit_edit redirects using Evennia's db_location_id field."""

    room_store, exit_store, _ = dummy_env
    redirect_call = {}

    def fake_redirect(viewname, **kwargs):
        redirect_call["viewname"] = viewname
        redirect_call["kwargs"] = kwargs
        response = HttpResponse(status=302)
        response["Location"] = f"/room/{kwargs['pk']}/"
        return response

    monkeypatch.setattr(views, "redirect", fake_redirect)
    ex = views.ObjectDB.objects.create(
        typeclass_path="", db_key="north", db_location=room_store[1], db_destination=room_store[2]
    )
    request = attach_user(rf.post(
        f"/exit/{ex.id}/edit/",
        {
            "key": "east",
            "destination": "2",
            "description": "desc",
            "lockstring": "",
            "err_msg": "",
            "aliases": "e,east",
        },
    ))
    resp = views.exit_edit(request, pk=ex.id)
    assert resp.status_code == 302
    assert resp["Location"] == "/room/1/"
    assert redirect_call == {"viewname": "roomeditor:room_edit", "kwargs": {"pk": 1}}
    assert exit_store[ex.id].aliases.all() == ["e", "east"]


def test_exit_delete_ajax_removes_exit(rf, dummy_env):
    """exit_delete removes exits via AJAX."""

    room_store, exit_store, _ = dummy_env
    ex = views.ObjectDB.objects.create(
        typeclass_path="", db_key="north", db_location=room_store[1], db_destination=room_store[2]
    )
    request = attach_user(rf.post(f"/exit/{ex.id}/delete/", HTTP_X_REQUESTED_WITH="XMLHttpRequest"))
    resp = views.exit_delete(request, pk=ex.id)
    assert json.loads(resp.content)["ok"] is True
    assert ex.id not in exit_store


def test_exit_delete_non_ajax_redirects_to_exit_location(rf, dummy_env, monkeypatch):
    """exit_delete redirects using Evennia's db_location_id field."""

    room_store, exit_store, _ = dummy_env
    redirect_call = {}

    def fake_redirect(viewname, **kwargs):
        redirect_call["viewname"] = viewname
        redirect_call["kwargs"] = kwargs
        response = HttpResponse(status=302)
        response["Location"] = f"/room/{kwargs['pk']}/"
        return response

    monkeypatch.setattr(views, "redirect", fake_redirect)
    ex = views.ObjectDB.objects.create(
        typeclass_path="", db_key="north", db_location=room_store[1], db_destination=room_store[2]
    )
    request = attach_user(rf.post(f"/exit/{ex.id}/delete/"))
    resp = views.exit_delete(request, pk=ex.id)
    assert resp.status_code == 302
    assert resp["Location"] == "/room/1/"
    assert redirect_call == {"viewname": "roomeditor:room_edit", "kwargs": {"pk": 1}}
    assert ex.id not in exit_store


def test_room_edit_warning_and_ajax_save(rf, dummy_env):
    """room_edit warns on missing incoming exits and saves via AJAX."""

    room_store, exit_store, captured = dummy_env
    request = attach_user(rf.get("/room/1/"))
    views.room_edit(request, pk=1)
    assert captured["template"] == "roomeditor/room_form.html"
    assert captured["context"]["has_incoming"] is False

    request = attach_user(rf.post(
        "/room/1/",
        {"db_key": "Hall", "db_desc": "desc"},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    ))
    resp = views.room_edit(request, pk=1)
    assert json.loads(resp.content)["ok"] is True
    assert room_store[1].key == "Hall"
    assert room_store[1].db.desc == "desc"


def test_room_list_marks_dangling_rooms(rf, dummy_env):
    """room_list should expose dangling room ids for the template."""

    room_store, exit_store, captured = dummy_env
    views.ObjectDB.objects.create(
        typeclass_path="", db_key="north", db_location=room_store[1], db_destination=room_store[2]
    )
    request = attach_user(rf.get("/rooms/"))
    views.room_list(request)
    assert captured["template"] == "roomeditor/room_list.html"
    assert captured["context"]["dangling_ids"] == {1}


def test_room_new_ajax_create_and_invalid_form(rf, dummy_env, monkeypatch):
    """room_new creates rooms over AJAX and reports validation errors."""

    room_store, exit_store, captured = dummy_env
    request = attach_user(rf.post(
        "/rooms/new/",
        {"db_key": "Lab", "desc": "A clean test lab."},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    ))
    resp = views.room_new(request)
    data = json.loads(resp.content)
    assert data == {"ok": True, "row_html": "ROOM:Lab"}
    room = next(room for room in room_store.values() if room.key == "Lab")
    assert room.typeclass_path == "typeclasses.rooms.Room"
    call = captured["create_calls"][-1]
    assert call["typeclass"] == "typeclasses.rooms.Room"
    assert call["key"] == "Lab"
    assert call["attributes"] == [("desc", "A clean test lab.")]

    class InvalidRoomForm:
        class Errors:
            def as_text(self):
                return "Name is required."

        errors = Errors()

        def __init__(self, data=None, instance=None):
            pass

        def is_valid(self):
            return False

    monkeypatch.setattr(views, "RoomForm", InvalidRoomForm)
    request = attach_user(rf.post("/rooms/new/", {"db_key": ""}, HTTP_X_REQUESTED_WITH="XMLHttpRequest"))
    resp = views.room_new(request)
    assert resp.status_code == 400
    assert json.loads(resp.content) == {"ok": False, "error": "Name is required."}


def test_room_search_api_filters_rooms(rf, dummy_env):
    """room_search_api returns matching rooms for autocomplete."""

    request = attach_user(rf.get("/api/rooms/", {"q": "R2"}))
    resp = views.room_search_api(request)
    assert json.loads(resp.content) == {"results": [{"id": 2, "text": "R2 (#2)"}]}


def test_builder_access_predicate():
    """Builder access should use superuser or Evennia Builder permissions."""

    assert has_builder_access(DummyUser(builder=True)) is True
    assert has_builder_access(DummyUser(builder=False, superuser=True)) is True
    assert has_builder_access(DummyUser(builder=False)) is False
    assert has_builder_access(DummyUser(authenticated=False, builder=True)) is False


def test_roomeditor_views_reject_unauthorized_users(rf):
    """Anonymous users redirect and authenticated non-builders are denied."""

    request = attach_user(rf.get("/rooms/"), DummyUser(authenticated=False, builder=False))
    response = views.room_list(request)
    assert response.status_code == 302

    request = attach_user(rf.get("/rooms/"), DummyUser(builder=False))
    with pytest.raises(PermissionDenied):
        views.room_list(request)

    request = attach_user(rf.post("/locks/validate/", {"lockstring": "all()"}), DummyUser(builder=False))
    with pytest.raises(PermissionDenied):
        locks.api_validate_lockstring(request)


def test_lock_validation_api_allows_builders(rf, monkeypatch):
    """Lock validation remains available to builders."""

    monkeypatch.setattr(locks, "validate_lockstring", lambda lockstring: (True, f"ok:{lockstring}"))
    request = attach_user(rf.post("/locks/validate/", {"lockstring": "all()"}))
    resp = locks.api_validate_lockstring(request)
    assert json.loads(resp.content) == {"ok": True, "message": "ok:all()"}

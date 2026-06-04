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
sys.modules.setdefault("evennia", fake_evennia)
sys.modules.setdefault("evennia.objects", fake_objects)
sys.modules.setdefault("evennia.objects.models", fake_models)

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
        self.destination = db_destination
        self.db_destination = db_destination
        self.db_location_id = getattr(db_location, "id", db_location)
        self.db_destination_id = getattr(db_destination, "id", db_destination)
        self.destination_id = getattr(db_destination, "id", db_destination)
        self.aliases = DummyAliases()
        self.locks = DummyLocks()
        self.db = types.SimpleNamespace(desc="", err_traverse="")

    def save(self):
        pass

    def delete(self):
        pass


class DummyRoom:
    def __init__(self, pk, key="Room"):
        self.id = pk
        self.pk = pk
        self.key = key
        self.db_key = key
        self.typeclass_path = "typeclasses.rooms.Room"
        self.db = types.SimpleNamespace(desc="")
        self.locks = DummyLocks()

    def delete(self):
        pass


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

    captured = {"template": None, "context": None}

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
    monkeypatch.setattr(views, "ExitForm", DummyExitForm)
    monkeypatch.setattr(views, "RoomForm", DummyRoomForm)
    monkeypatch.setattr(views, "render", fake_render)
    monkeypatch.setattr(views, "reverse_dir", lambda key: f"{key}-rev")

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
    request = attach_user(rf.post("/rooms/new/", {"db_key": "Lab"}, HTTP_X_REQUESTED_WITH="XMLHttpRequest"))
    resp = views.room_new(request)
    data = json.loads(resp.content)
    assert data == {"ok": True, "row_html": "ROOM:Lab"}
    room = next(room for room in room_store.values() if room.key == "Lab")
    assert room.typeclass_path == "typeclasses.rooms.Room"

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

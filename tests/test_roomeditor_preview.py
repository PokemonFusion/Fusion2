"""Tests for room editor views and AJAX behavior."""
import json
import sys
import types

import django
import pytest
from django.conf import settings
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


class DummyAliases:
    """Simple alias container."""

    def __init__(self):
        self.aliases = []

    def add(self, *vals):
        self.aliases.extend(vals)

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

    def __init__(self, db_key, db_location, db_destination, typeclass_path=""):
        self.id = DummyExit._counter
        DummyExit._counter += 1
        self.key = db_key
        self.db_key = db_key
        self.location_id = getattr(db_location, "id", db_location)
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
        self.key = key
        self.db = types.SimpleNamespace(desc="")


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
                attr = k.replace("db_", "")
                if getattr(ex, attr) != v:
                    match = False
                    break
            if match:
                results.append(ex)
        return ExitQuery(results)


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

    class DummyObjectDB:
        class Manager:
            def create(self, **kwargs):
                return create_exit(**kwargs)

        objects = Manager()

    room_manager = object()
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
        return HttpResponse("FORM")

    monkeypatch.setattr(views, "_room_qs", lambda: room_manager)
    monkeypatch.setattr(views, "_exit_qs", lambda: exit_manager)
    monkeypatch.setattr(views, "get_object_or_404", fake_get_object_or_404)
    monkeypatch.setattr(views, "ObjectDB", DummyObjectDB)
    monkeypatch.setattr(views, "DefaultExit", types.SimpleNamespace(path="evennia.default_exit"))
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
    request = rf.post("/ansi/preview/", {"text": "|rred|n"})
    resp = views.ansi_preview(request)
    assert json.loads(resp.content) == {"html": "<p>|rred|n</p>"}


def test_exit_new_get_and_ajax_create(rf, dummy_env):
    """exit_new renders form and creates exits via AJAX."""

    room_store, exit_store, captured = dummy_env
    request = rf.get("/exit/new/1/")
    views.exit_new(request, room_pk=1)
    assert captured["template"] == "roomeditor/_exit_form.html"

    request = rf.post(
        "/exit/new/1/",
        {"key": "north", "destination": "2"},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    resp = views.exit_new(request, room_pk=1)
    assert captured["template"] == "roomeditor/_exit_row.html"
    data = json.loads(resp.content)
    assert data["ok"] is True
    assert data["row_html"] == "ROW:north"
    assert any(ex.key == "north" for ex in exit_store.values())


def test_exit_edit_ajax_updates_exit(rf, dummy_env):
    """exit_edit updates an existing exit and returns new row HTML."""

    room_store, exit_store, captured = dummy_env
    ex = views.ObjectDB.objects.create(
        typeclass_path="", db_key="north", db_location=room_store[1], db_destination=room_store[2]
    )
    request = rf.post(
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
    )
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


def test_exit_delete_ajax_removes_exit(rf, dummy_env):
    """exit_delete removes exits via AJAX."""

    room_store, exit_store, _ = dummy_env
    ex = views.ObjectDB.objects.create(
        typeclass_path="", db_key="north", db_location=room_store[1], db_destination=room_store[2]
    )
    request = rf.post(f"/exit/{ex.id}/delete/", HTTP_X_REQUESTED_WITH="XMLHttpRequest")
    resp = views.exit_delete(request, pk=ex.id)
    assert json.loads(resp.content)["ok"] is True
    assert ex.id not in exit_store


def test_room_edit_warning_and_ajax_save(rf, dummy_env):
    """room_edit warns on missing incoming exits and saves via AJAX."""

    room_store, exit_store, captured = dummy_env
    request = rf.get("/room/1/")
    views.room_edit(request, pk=1)
    assert captured["template"] == "roomeditor/room_form.html"
    assert captured["context"]["has_incoming"] is False

    request = rf.post(
        "/room/1/",
        {"db_key": "Hall", "db_desc": "desc"},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    resp = views.room_edit(request, pk=1)
    assert json.loads(resp.content)["ok"] is True
    assert room_store[1].key == "Hall"
    assert room_store[1].db.desc == "desc"

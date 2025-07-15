import os
import sys
import types
from django.http import HttpResponse
from django.test import RequestFactory
from django.conf import settings

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_preview_context():
    import importlib
    if not settings.configured:
        settings.configure(
            SECRET_KEY="test",
            DEFAULT_CHARSET="utf-8",
            INSTALLED_APPS=[],
            USE_I18N=False,
            ROOT_URLCONF="tests.urls",
        )
        import django
        django.setup()
    prev_evennia = sys.modules.get("evennia")
    prev_objects = sys.modules.get("evennia.objects")
    prev_models = sys.modules.get("evennia.objects.models")
    prev_rooms = sys.modules.get("typeclasses.rooms")
    prev_exits = sys.modules.get("typeclasses.exits")

    fake_evennia = types.ModuleType("evennia")

    def fake_create_object(*a, **k):
        obj = types.SimpleNamespace(id=1, key=k.get("key"))
        obj.db = types.SimpleNamespace()
        obj.typeclass_path = a[0]
        obj.swap_typeclass = lambda *args, **kw: None
        obj.save = lambda: None
        return obj

    fake_evennia.create_object = fake_create_object
    fake_objects = types.ModuleType("evennia.objects")
    fake_models = types.ModuleType("evennia.objects.models")

    class DummyQuery:
        def filter(self, *a, **k):
            return []

        def exists(self):
            return False

    fake_models.ObjectDB = type("ObjectDB", (), {"objects": DummyQuery()})
    fake_evennia.objects = fake_objects
    sys.modules["evennia"] = fake_evennia
    sys.modules["evennia.objects"] = fake_objects
    sys.modules["evennia.objects.models"] = fake_models
    sys.modules.setdefault("typeclasses.rooms", types.ModuleType("typeclasses.rooms"))
    sys.modules.setdefault("typeclasses.exits", types.ModuleType("typeclasses.exits"))
    sys.modules["typeclasses.rooms"].Room = type("Room", (), {})
    sys.modules["typeclasses.exits"].Exit = type("Exit", (), {})

    views = importlib.import_module("roomeditor.views")
    rf = RequestFactory()
    data = {
        "room_class": "typeclasses.rooms.Room",
        "name": "Test Room",
        "desc": "A sample room",
        "is_center": True,
        "is_shop": False,
        "has_hunting": True,
        "hunt_table": "Pikachu:5",
        "preview_room": "1",
    }
    request = rf.post("/roomeditor/new/", data)
    request.user = types.SimpleNamespace(is_authenticated=True, is_superuser=True)

    captured = {}

    def fake_render(req, tpl, ctx):
        captured["template"] = tpl
        captured["context"] = ctx
        return HttpResponse()

    orig_render = views.render
    views.render = fake_render
    try:
        views.room_edit.__wrapped__(request)
    finally:
        views.render = orig_render
        if prev_evennia is not None:
            sys.modules["evennia"] = prev_evennia
        else:
            sys.modules.pop("evennia", None)
        if prev_objects is not None:
            sys.modules["evennia.objects"] = prev_objects
        else:
            sys.modules.pop("evennia.objects", None)
        if prev_models is not None:
            sys.modules["evennia.objects.models"] = prev_models
        else:
            sys.modules.pop("evennia.objects.models", None)
        if prev_rooms is not None:
            sys.modules["typeclasses.rooms"] = prev_rooms
        else:
            sys.modules.pop("typeclasses.rooms", None)
        if prev_exits is not None:
            sys.modules["typeclasses.exits"] = prev_exits
        else:
            sys.modules.pop("typeclasses.exits", None)

    assert captured.get("template") == "roomeditor/room_preview.html"
    assert "preview" in captured.get("context", {})
    assert captured["context"]["preview"]["name"] == "Test Room"


def test_save_redirects_to_list():
    import importlib
    from django.urls import reverse
    if not settings.configured:
        settings.configure(
            SECRET_KEY="test",
            DEFAULT_CHARSET="utf-8",
            INSTALLED_APPS=[],
            USE_I18N=False,
            ROOT_URLCONF="tests.urls",
        )
        import django
        django.setup()
    prev_evennia = sys.modules.get("evennia")
    prev_objects = sys.modules.get("evennia.objects")
    prev_models = sys.modules.get("evennia.objects.models")
    prev_rooms = sys.modules.get("typeclasses.rooms")
    prev_exits = sys.modules.get("typeclasses.exits")

    fake_evennia = types.ModuleType("evennia")

    def fake_create_object(*a, **k):
        obj = types.SimpleNamespace(id=1, key=k.get("key"))
        obj.db = types.SimpleNamespace()
        obj.typeclass_path = a[0]
        obj.swap_typeclass = lambda *args, **kw: None
        obj.save = lambda: None
        return obj

    fake_evennia.create_object = fake_create_object
    fake_objects = types.ModuleType("evennia.objects")
    fake_models = types.ModuleType("evennia.objects.models")

    class DummyQuery:
        def filter(self, *a, **k):
            return []

        def exists(self):
            return False

    fake_models.ObjectDB = type("ObjectDB", (), {"objects": DummyQuery()})
    fake_evennia.objects = fake_objects
    sys.modules["evennia"] = fake_evennia
    sys.modules["evennia.objects"] = fake_objects
    sys.modules["evennia.objects.models"] = fake_models
    sys.modules.setdefault("typeclasses.rooms", types.ModuleType("typeclasses.rooms"))
    sys.modules.setdefault("typeclasses.exits", types.ModuleType("typeclasses.exits"))
    sys.modules["typeclasses.rooms"].Room = type("Room", (), {})
    sys.modules["typeclasses.exits"].Exit = type("Exit", (), {})

    views = importlib.import_module("roomeditor.views")
    rf = RequestFactory()
    data = {
        "room_class": "typeclasses.rooms.Room",
        "name": "Test Room",
        "desc": "A sample room",
        "is_center": False,
        "is_shop": False,
        "has_hunting": False,
        "hunt_table": "",
        "save_room": "1",
    }
    request = rf.post("/roomeditor/new/", data)
    request.user = types.SimpleNamespace(is_authenticated=True, is_superuser=True)

    try:
        resp = views.room_edit.__wrapped__(request)
    finally:
        if prev_evennia is not None:
            sys.modules["evennia"] = prev_evennia
        else:
            sys.modules.pop("evennia", None)
        if prev_objects is not None:
            sys.modules["evennia.objects"] = prev_objects
        else:
            sys.modules.pop("evennia.objects", None)
        if prev_models is not None:
            sys.modules["evennia.objects.models"] = prev_models
        else:
            sys.modules.pop("evennia.objects.models", None)
        if prev_rooms is not None:
            sys.modules["typeclasses.rooms"] = prev_rooms
        else:
            sys.modules.pop("typeclasses.rooms", None)
        if prev_exits is not None:
            sys.modules["typeclasses.exits"] = prev_exits
        else:
            sys.modules.pop("typeclasses.exits", None)

    assert resp.status_code == 302
    assert resp.url == reverse("roomeditor:room-list")

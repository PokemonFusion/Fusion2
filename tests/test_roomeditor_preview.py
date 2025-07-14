import importlib
import types
import os
import sys
from django.http import HttpResponse
from django.test import RequestFactory
from django.conf import settings

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

def test_room_preview_html():
    if not settings.configured:
        settings.configure(
            SECRET_KEY="test",
            DEFAULT_CHARSET="utf-8",
            INSTALLED_APPS=[],
            USE_I18N=False,
        )
        import django
        django.setup()

    prev_evennia = sys.modules.get("evennia")
    prev_objects = sys.modules.get("evennia.objects")
    prev_models = sys.modules.get("evennia.objects.models")

    fake_evennia = types.ModuleType("evennia")
    fake_evennia.create_object = lambda *a, **k: None
    fake_evennia.search_object = lambda *a, **k: []
    fake_objects = types.ModuleType("evennia.objects")
    fake_models = types.ModuleType("evennia.objects.models")

    fake_models.ObjectDB = type("ObjectDB", (), {"objects": types.SimpleNamespace(filter=lambda *a, **k: [] )})
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
        "name": "Test Room",
        "desc": "A \u001b[31mred\u001b[0m room",
        "is_center": False,
        "is_shop": False,
        "has_hunting": False,
        "hunt_table": "",
    }
    request = rf.post("/roomeditor/preview/", data)
    request.user = types.SimpleNamespace(is_authenticated=True, is_superuser=True)

    captured = {}

    def fake_render(req, tpl, ctx):
        captured.update(ctx)
        return HttpResponse()

    orig_render = views.render
    fake_text2html = types.ModuleType("evennia.utils.text2html")
    fake_text2html.parse_html = lambda text: f"PARSED:{text}"
    sys.modules["evennia.utils.text2html"] = fake_text2html
    views.render = fake_render
    try:
        views.room_preview.__wrapped__(request)
    finally:
        views.render = orig_render
        sys.modules.pop("evennia.utils.text2html", None)
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
        sys.modules.pop("typeclasses.rooms", None)
        sys.modules.pop("typeclasses.exits", None)

    assert captured["name"] == "Test Room"
    assert captured["desc_html"] == "PARSED:A \u001b[31mred\u001b[0m room"

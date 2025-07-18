import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

class DummyDB(types.SimpleNamespace):
    def get(self, key, default=None):
        return getattr(self, key, default)


def test_get_weather_handles_get_attribute_shadow():
    prev_evennia = sys.modules.get("evennia")
    prev_obj = sys.modules.get("evennia.objects")
    prev_obj_obj = sys.modules.get("evennia.objects.objects")
    prev_tc_objects = sys.modules.get("typeclasses.objects")

    evennia = types.ModuleType("evennia")
    fake_objects = types.ModuleType("evennia.objects")
    fake_objects_objects = types.ModuleType("evennia.objects.objects")
    DefaultRoom = type("DefaultRoom", (), {})
    DefaultObject = type("DefaultObject", (), {})
    fake_objects_objects.DefaultRoom = DefaultRoom
    fake_objects_objects.DefaultObject = DefaultObject
    fake_objects.objects = fake_objects_objects
    evennia.objects = fake_objects
    fake_utils = types.ModuleType("evennia.utils")
    fake_utils.ansi = types.SimpleNamespace(parse_ansi=lambda txt: txt)
    evennia.utils = fake_utils
    sys.modules["evennia"] = evennia
    sys.modules["evennia.objects"] = fake_objects
    sys.modules["evennia.objects.objects"] = fake_objects_objects
    sys.modules["evennia.utils"] = fake_utils
    # Minimal stub for typeclasses.objects required by rooms.py
    fake_tc_objects = types.ModuleType("typeclasses.objects")
    fake_tc_objects.ObjectParent = type("ObjectParent", (), {})
    sys.modules["typeclasses.objects"] = fake_tc_objects

    try:
        import importlib.util
        import types as pytypes

        # load the rooms module from file without relying on the original package
        spec = importlib.util.spec_from_file_location(
            "typeclasses.rooms",
            os.path.join(ROOT, "typeclasses", "rooms.py"),
        )
        rooms = importlib.util.module_from_spec(spec)
        sys.modules.setdefault("typeclasses", pytypes.ModuleType("typeclasses"))
        sys.modules["typeclasses"].rooms = rooms
        sys.modules["typeclasses.rooms"] = rooms
        spec.loader.exec_module(rooms)
        FusionRoom = rooms.FusionRoom
        room = FusionRoom()
        room.db = DummyDB(weather="rain")
        assert room.get_weather() == "rain"
        # Store an attribute named 'get' which could shadow the handler's method
        room.db.get = None
        assert room.get_weather() == "rain"
    finally:
        if prev_evennia is not None:
            sys.modules["evennia"] = prev_evennia
        else:
            sys.modules.pop("evennia", None)
        if prev_obj is not None:
            sys.modules["evennia.objects"] = prev_obj
        else:
            sys.modules.pop("evennia.objects", None)
        if prev_obj_obj is not None:
            sys.modules["evennia.objects.objects"] = prev_obj_obj
        else:
            sys.modules.pop("evennia.objects.objects", None)
        if prev_tc_objects is not None:
            sys.modules["typeclasses.objects"] = prev_tc_objects
        else:
            sys.modules.pop("typeclasses.objects", None)

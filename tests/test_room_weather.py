import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Provide a minimal evennia stub if the real module isn't available
if "evennia" not in sys.modules:
    evennia = types.ModuleType("evennia")
    evennia.DefaultRoom = type("DefaultRoom", (), {})
    evennia.objects = types.SimpleNamespace(objects=types.SimpleNamespace(DefaultRoom=evennia.DefaultRoom))
    sys.modules["evennia"] = evennia

# ensure battle storage module can be imported
storage_path = os.path.join(ROOT, "pokemon", "battle", "storage.py")
storage_spec = importlib.util.spec_from_file_location("pokemon.battle.storage", storage_path)
storage_mod = importlib.util.module_from_spec(storage_spec)
sys.modules[storage_spec.name] = storage_mod
storage_spec.loader.exec_module(storage_mod)

from world.hunt_system import HuntSystem


class DummyDB(types.SimpleNamespace):
    def get(self, key, default=None):
        return getattr(self, key, default)

class DummyRoom:
    def __init__(self, weather="clear"):
        self.db = DummyDB(weather=weather, allow_hunting=True)

def test_hunt_system_uses_room_weather():
    room = DummyRoom(weather="rain")
    hs = HuntSystem(room)
    assert hs.get_current_weather() == "rain"
    room.db.weather = "sunny"
    assert hs.get_current_weather() == "sunny"

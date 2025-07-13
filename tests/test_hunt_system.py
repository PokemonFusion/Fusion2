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

from world.hunt_system import HuntSystem


class DummyDB(types.SimpleNamespace):
    def get(self, key, default=None):
        return getattr(self, key, default)


class DummyRoom:
    def __init__(self):
        # use a 0 encounter rate to ensure fixed hunts ignore it
        self.db = DummyDB(allow_hunting=True, encounter_rate=0)


def test_perform_fixed_hunt():
    room = DummyRoom()
    captured = {}

    def cb(hunter, data):
        captured.update(data)

    hs = HuntSystem(room, spawn_callback=cb)
    msg = hs.perform_fixed_hunt(object(), "Pikachu", 7)
    assert msg == "A wild Pikachu (Lv 7) appeared!"
    assert captured["name"] == "Pikachu"
    assert captured["level"] == 7

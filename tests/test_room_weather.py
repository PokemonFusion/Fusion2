import os
import sys
import types
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

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

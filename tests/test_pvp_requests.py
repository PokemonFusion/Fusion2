import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_pvp_module():
    path = os.path.join(ROOT, "pokemon", "battle", "pvp.py")
    spec = importlib.util.spec_from_file_location("pokemon.battle.pvp", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_character_module():
    path = os.path.join(ROOT, "typeclasses", "characters.py")
    spec = importlib.util.spec_from_file_location("typeclasses.characters", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def setup_evennia():
    """Install minimal evennia stubs."""
    orig_evennia = sys.modules.get("evennia")
    fake_evennia = types.ModuleType("evennia")
    sys.modules["evennia"] = fake_evennia
    objects_mod = types.ModuleType("evennia.objects")
    objs = types.ModuleType("evennia.objects.objects")

    class DefaultObj:
        def at_pre_move(self, destination, **kwargs):
            return True

        def msg(self, text):
            pass

    DefaultChar = DefaultObj

    objs.DefaultCharacter = DefaultChar
    objs.DefaultObject = DefaultObj
    objects_mod.objects = objs
    fake_evennia.objects = objects_mod

    def search_object(obj_id):
        return [types.SimpleNamespace(id=obj_id)]

    fake_evennia.search_object = search_object
    sys.modules["evennia.objects"] = objects_mod
    sys.modules["evennia.objects.objects"] = objs

    utils_mod = types.ModuleType("evennia.utils")
    utils_utils = types.ModuleType("evennia.utils.utils")
    utils_utils.inherits_from = lambda obj, parent: isinstance(obj, parent)
    utils_mod.utils = utils_utils
    sys.modules["evennia.utils"] = utils_mod
    sys.modules["evennia.utils.utils"] = utils_utils

    return orig_evennia


def restore_evennia(orig):
    if orig is not None:
        sys.modules["evennia"] = orig
    else:
        sys.modules.pop("evennia", None)
    sys.modules.pop("evennia.objects.objects", None)
    sys.modules.pop("evennia.objects", None)
    sys.modules.pop("evennia.utils", None)
    sys.modules.pop("evennia.utils.utils", None)


class FakeRoom:
    def __init__(self):
        class CountingDB:
            def __init__(self):
                self._vals = {}
                self.sets = 0

            def __getattr__(self, key):
                return self._vals.get(key)

            def __setattr__(self, key, value):
                if key in {"_vals", "sets"}:
                    object.__setattr__(self, key, value)
                else:
                    self._vals[key] = value
                    self.sets += 1

        self.db = CountingDB()
        self.msgs = []

    def msg_contents(self, text):
        self.msgs.append(text)


def test_create_request_locks_and_announces():
    orig = setup_evennia()
    pvp = load_pvp_module()

    room = FakeRoom()
    host = types.SimpleNamespace(id=1, key="Alice", location=room, db=types.SimpleNamespace())

    req = pvp.create_request(host)

    assert room.db.pvp_requests[1] is req
    assert getattr(host.db, "pvp_locked", False) is True
    assert room.msgs and "alice" in room.msgs[0].lower()
    assert room.db.sets >= 2

    restore_evennia(orig)


def test_remove_request_unlocks():
    orig = setup_evennia()
    pvp = load_pvp_module()

    room = FakeRoom()
    host = types.SimpleNamespace(id=1, key="Alice", location=room, db=types.SimpleNamespace())

    pvp.create_request(host)
    pvp.remove_request(host)

    assert room.db.pvp_requests == {}
    assert getattr(host.db, "pvp_locked", False) is False
    assert room.db.sets >= 3

    restore_evennia(orig)


def test_character_cannot_move_when_locked():
    orig = setup_evennia()
    char_mod = load_character_module()

    char = char_mod.Character()
    char.db = types.SimpleNamespace(pvp_locked=True)
    msgs = []
    char.msg = lambda text: msgs.append(text)

    result = char.at_pre_move(None)
    assert result is False
    assert msgs and "pvp" in msgs[0].lower()

    char.db.pvp_locked = False
    msgs.clear()
    assert char.at_pre_move(None) is True

    restore_evennia(orig)


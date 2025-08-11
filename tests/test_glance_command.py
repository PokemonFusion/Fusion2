import os
import sys
import types
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module():
    path = os.path.join(ROOT, "commands", "player", "cmd_glance.py")
    spec = importlib.util.spec_from_file_location("commands.player.cmd_glance", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_glance_lists_online_characters():
    orig_evennia = sys.modules.get("evennia")
    orig_utils = sys.modules.get("evennia.utils")
    orig_utils_evtable = sys.modules.get("evennia.utils.evtable")
    orig_utils_utils = sys.modules.get("evennia.utils.utils")

    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    fake_obj_mod = types.ModuleType("evennia.objects.objects")
    fake_obj_mod.DefaultCharacter = type("DefaultCharacter", (), {})
    fake_objects_pkg = types.ModuleType("evennia.objects")
    fake_objects_pkg.objects = fake_obj_mod
    fake_evennia.objects = fake_objects_pkg
    sys.modules["evennia"] = fake_evennia
    sys.modules["evennia.objects"] = fake_objects_pkg
    sys.modules["evennia.objects.objects"] = fake_obj_mod

    table_rows = []

    class FakeEvTable:
        def __init__(self, *cols):
            self.rows = []

        def add_row(self, *vals):
            self.rows.append(vals)

        def __str__(self):
            table_rows.extend(self.rows)
            return "TABLE"

    fake_evtable_mod = types.ModuleType("evennia.utils.evtable")
    fake_evtable_mod.EvTable = FakeEvTable
    sys.modules["evennia.utils.evtable"] = fake_evtable_mod

    fake_utils_utils_mod = types.ModuleType("evennia.utils.utils")
    fake_utils_utils_mod.time_format = lambda sec, digits=1: f"{int(sec)}s"
    sys.modules["evennia.utils.utils"] = fake_utils_utils_mod

    fake_utils_pkg = types.ModuleType("evennia.utils")
    fake_utils_pkg.evtable = fake_evtable_mod
    fake_utils_pkg.utils = fake_utils_utils_mod
    sys.modules["evennia.utils"] = fake_utils_pkg

    cmd_mod = load_cmd_module()

    # restore modules
    if orig_evennia is not None:
        sys.modules["evennia"] = orig_evennia
    else:
        sys.modules.pop("evennia", None)
    sys.modules.pop("evennia.objects", None)
    sys.modules.pop("evennia.objects.objects", None)
    if orig_utils is not None:
        sys.modules["evennia.utils"] = orig_utils
    else:
        sys.modules.pop("evennia.utils", None)
    if orig_utils_evtable is not None:
        sys.modules["evennia.utils.evtable"] = orig_utils_evtable
    else:
        sys.modules.pop("evennia.utils.evtable", None)
    if orig_utils_utils is not None:
        sys.modules["evennia.utils.utils"] = orig_utils_utils
    else:
        sys.modules.pop("evennia.utils.utils", None)

    class DummySessions:
        def __init__(self, have=True):
            self.have = have

        def all(self):
            return [object()] if self.have else []

    class DummyChar:
        def __init__(self, key, gender=None, species=None, idle=0, online=True):
            self.key = key
            self.db = types.SimpleNamespace(gender=gender, fusion_species=species)
            self.sessions = DummySessions(online)
            self.idle_time = idle
            self.msgs = []
            self.location = None

        def is_typeclass(self, *args, **kwargs):
            return True

        def msg(self, text):
            self.msgs.append(text)

    class DummyRoom:
        def __init__(self, contents):
            self.contents = contents

    online = DummyChar("On", "M", "Pikachu", idle=5, online=True)
    offline = DummyChar("Off", online=False)
    caller = DummyChar("Caller", "F", "Trainer", idle=1, online=True)
    room = DummyRoom([online, offline, caller])
    caller.location = room

    cmd = cmd_mod.CmdGlance()
    cmd.caller = caller
    cmd.func()

    assert table_rows
    names = [row[0] for row in table_rows]
    assert "On" in names and "Caller" in names
    assert "Off" not in names
    assert caller.msgs and caller.msgs[-1] == "TABLE"

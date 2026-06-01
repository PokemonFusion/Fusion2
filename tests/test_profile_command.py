import importlib.util
import os
import sys
import types


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module(search_results=None):
    originals = {name: sys.modules.get(name) for name in (
        "evennia",
        "evennia.objects",
        "evennia.objects.objects",
        "evennia.utils",
        "evennia.utils.evtable",
    )}

    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    fake_evennia.search_object = lambda *args, **kwargs: list(search_results or [])
    sys.modules["evennia"] = fake_evennia

    fake_obj_mod = types.ModuleType("evennia.objects.objects")
    fake_obj_mod.DefaultCharacter = type("DefaultCharacter", (), {})
    fake_objects_pkg = types.ModuleType("evennia.objects")
    fake_objects_pkg.objects = fake_obj_mod
    sys.modules["evennia.objects"] = fake_objects_pkg
    sys.modules["evennia.objects.objects"] = fake_obj_mod

    class FakeEvTable:
        def __init__(self, *cols):
            self.cols = cols
            self.rows = []

        def add_row(self, *vals):
            self.rows.append(vals)

        def __str__(self):
            return repr({"cols": self.cols, "rows": self.rows})

    fake_evtable_mod = types.ModuleType("evennia.utils.evtable")
    fake_evtable_mod.EvTable = FakeEvTable
    fake_utils_pkg = types.ModuleType("evennia.utils")
    fake_utils_pkg.evtable = fake_evtable_mod
    sys.modules["evennia.utils"] = fake_utils_pkg
    sys.modules["evennia.utils.evtable"] = fake_evtable_mod

    path = os.path.join(ROOT, "commands", "player", "cmd_profile.py")
    spec = importlib.util.spec_from_file_location("commands.player.cmd_profile", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

    def restore():
        sys.modules.pop("commands.player.cmd_profile", None)
        for name, original in originals.items():
            if original is not None:
                sys.modules[name] = original
            else:
                sys.modules.pop(name, None)

    return mod, restore


class DummyChar:
    def __init__(self, key, ident=1, perms=None):
        self.key = key
        self.name = key
        self.id = ident
        self.db = types.SimpleNamespace()
        self.messages = []
        self.perms = set(perms or [])

    def is_typeclass(self, *args, **kwargs):
        return True

    def msg(self, text):
        self.messages.append(text)

    def check_permstring(self, perm):
        return perm in self.perms


def call_profile(mod, caller, args="", switches=None, lhs="", rhs=""):
    cmd = mod.CmdProfile()
    cmd.caller = caller
    cmd.args = args
    cmd.switches = switches or []
    cmd.lhs = lhs
    cmd.rhs = rhs
    cmd.func()
    return caller.messages[-1]


def test_profile_command_exposes_legacy_aliases():
    mod, restore = load_cmd_module()
    try:
        assert mod.CmdProfile.key == "+profile"
        assert mod.CmdProfile.aliases == ["+finger", "+info"]
    finally:
        restore()


def test_profile_set_and_view_own_fields():
    caller = DummyChar("Ash")
    mod, restore = load_cmd_module()
    try:
        saved = call_profile(mod, caller, switches=["set"], lhs="Appearance", rhs="Red jacket.")
        output = call_profile(mod, caller)
    finally:
        restore()

    assert saved == "Profile field 'Appearance' saved."
    assert "Profile for Ash" in output
    assert "Appearance" in output
    assert "Red jacket." in output


def test_profile_target_lookup_hides_private_fields_from_regular_viewer():
    owner = DummyChar("Misty", ident=2)
    viewer = DummyChar("Ash", ident=1)
    mod, restore = load_cmd_module([owner])
    try:
        mod.set_profile_field(owner, "Public", "Gym leader.")
        mod.set_profile_field(owner, "Secret", "Private note.", private=True)
        output = call_profile(mod, viewer, args="Misty")
    finally:
        restore()

    assert "Gym leader." in output
    assert "Private note." not in output
    assert "Secret" not in output


def test_profile_private_fields_visible_to_validator():
    owner = DummyChar("Misty", ident=2)
    viewer = DummyChar("Validator", ident=1, perms={"Validator"})
    mod, restore = load_cmd_module([owner])
    try:
        mod.set_profile_field(owner, "Secret", "Private note.", private=True)
        output = call_profile(mod, viewer, args="Misty")
    finally:
        restore()

    assert "Secret <PRIVATE>" in output
    assert "Private note." in output


def test_profile_delete_and_privacy_commands():
    caller = DummyChar("Ash")
    mod, restore = load_cmd_module()
    try:
        mod.set_profile_field(caller, "Title", "Trainer.")
        private = call_profile(mod, caller, args="Title", switches=["private"])
        deleted = call_profile(mod, caller, args="Title", switches=["del"])
        output = call_profile(mod, caller)
    finally:
        restore()

    assert private == "Profile field 'Title' is now private."
    assert deleted == "Profile field 'Title' deleted."
    assert output == "Ash has no visible profile fields."

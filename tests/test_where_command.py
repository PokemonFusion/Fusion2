import importlib.util
import os
import sys
import types


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module():
    path = os.path.join(ROOT, "commands", "player", "cmd_where.py")
    spec = importlib.util.spec_from_file_location("commands.player.cmd_where", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_with_fake_evennia(sessions):
    originals = {name: sys.modules.get(name) for name in (
        "evennia",
        "evennia.objects",
        "evennia.objects.objects",
        "evennia.utils",
        "evennia.utils.evtable",
        "evennia.utils.utils",
    )}

    class FakeSessionHandler:
        def get_sessions(self):
            return list(sessions)

    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    fake_evennia.SESSION_HANDLER = FakeSessionHandler()
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
    sys.modules["evennia.utils.evtable"] = fake_evtable_mod

    fake_utils_utils_mod = types.ModuleType("evennia.utils.utils")
    fake_utils_utils_mod.time_format = lambda sec, digits=1: f"{int(sec)}s"
    sys.modules["evennia.utils.utils"] = fake_utils_utils_mod

    fake_utils_pkg = types.ModuleType("evennia.utils")
    fake_utils_pkg.evtable = fake_evtable_mod
    fake_utils_pkg.utils = fake_utils_utils_mod
    sys.modules["evennia.utils"] = fake_utils_pkg

    mod = load_cmd_module()

    def restore():
        sys.modules.pop("commands.player.cmd_where", None)
        for name, original in originals.items():
            if original is not None:
                sys.modules[name] = original
            else:
                sys.modules.pop(name, None)

    return mod, restore


class DummySession:
    def __init__(self, puppet):
        self.puppet = puppet

    def get_puppet(self):
        return self.puppet


class DummyRoom:
    def __init__(self, key):
        self.key = key
        self.db = types.SimpleNamespace()


class DummyChar:
    def __init__(
        self,
        key,
        room=None,
        gender="Unknown",
        species="Human",
        idle=0,
        perms=None,
        can_edit_rooms=False,
    ):
        self.key = key
        self.name = key
        self.id = hash(key)
        self.location = room
        self.db = types.SimpleNamespace(gender=gender, fusion_species=species)
        self.idle_time = idle
        self.messages = []
        self.perms = set(perms or [])
        self.can_edit_rooms = can_edit_rooms

    def is_typeclass(self, *args, **kwargs):
        return True

    def msg(self, text):
        self.messages.append(text)

    def check_permstring(self, perm):
        return perm in self.perms

    def access(self, room, access_type):
        return self.can_edit_rooms and access_type == "edit"


def call_where(mod, caller, args=""):
    cmd = mod.CmdWhere()
    cmd.caller = caller
    cmd.args = args
    cmd.func()
    return caller.messages[-1]


def test_where_lists_online_characters_with_locations():
    town = DummyRoom("Town Square")
    center = DummyRoom("Pokemon Center")
    caller = DummyChar("Ash", town, gender="M", species="Pikachu", idle=5)
    misty = DummyChar("Misty", center, gender="F", species="Starmie", idle=12)
    mod, restore = load_with_fake_evennia([DummySession(caller), DummySession(misty)])

    try:
        output = call_where(mod, caller)
    finally:
        restore()

    assert "Ash" in output
    assert "Town Square" in output
    assert "Misty" in output
    assert "Pokemon Center" in output
    assert "5s" in output
    assert "12s" in output


def test_where_exposes_legacy_aliases():
    mod, restore = load_with_fake_evennia([])

    try:
        assert mod.CmdWhere.aliases == ["where", "wa"]
    finally:
        restore()


def test_where_player_privacy_hides_location_from_non_staff():
    town = DummyRoom("Town Square")
    center = DummyRoom("Pokemon Center")
    caller = DummyChar("Ash", town)
    misty = DummyChar("Misty", center)
    misty.db.where_private = True
    mod, restore = load_with_fake_evennia([DummySession(caller), DummySession(misty)])

    try:
        output = call_where(mod, caller)
    finally:
        restore()

    assert "Misty" in output
    assert "*Private*" in output
    assert "Pokemon Center" not in output


def test_where_staff_bypasses_privacy_and_sees_dark_characters():
    town = DummyRoom("Town Square")
    center = DummyRoom("Pokemon Center")
    caller = DummyChar("Admin", town, perms={"Admin"})
    hidden = DummyChar("Hidden", center)
    hidden.db.where_private = True
    hidden.db.dark = True
    mod, restore = load_with_fake_evennia([DummySession(caller), DummySession(hidden)])

    try:
        output = call_where(mod, caller)
    finally:
        restore()

    assert "Hidden (Dark)" in output
    assert "Pokemon Center" in output
    assert "*Private*" not in output


def test_where_non_staff_cannot_see_dark_characters():
    town = DummyRoom("Town Square")
    center = DummyRoom("Pokemon Center")
    caller = DummyChar("Ash", town)
    hidden = DummyChar("Hidden", center)
    hidden.db.dark = True
    mod, restore = load_with_fake_evennia([DummySession(caller), DummySession(hidden)])

    try:
        output = call_where(mod, caller)
    finally:
        restore()

    assert "Ash" in output
    assert "Hidden" not in output


def test_where_self_privacy_toggles():
    town = DummyRoom("Town Square")
    caller = DummyChar("Ash", town)
    mod, restore = load_with_fake_evennia([DummySession(caller)])

    try:
        hidden = call_where(mod, caller, "#private")
        assert hidden == "Your location is now hidden from +where."
        assert caller.db.where_private is True

        public = call_where(mod, caller, "#public")
        assert public == "Your location is now visible on +where."
        assert caller.db.where_private is False
    finally:
        restore()


def test_where_room_privacy_requires_room_control():
    town = DummyRoom("Town Square")
    caller = DummyChar("Ash", town)
    mod, restore = load_with_fake_evennia([DummySession(caller)])

    try:
        denied = call_where(mod, caller, "#roomprivate")
    finally:
        restore()

    assert denied == "You do not have permission to change this room's +where privacy."
    assert not getattr(town.db, "where_private", False)


def test_where_room_privacy_hides_everyone_in_room():
    town = DummyRoom("Town Square")
    center = DummyRoom("Pokemon Center")
    caller = DummyChar("Ash", town, can_edit_rooms=True)
    misty = DummyChar("Misty", town)
    brock = DummyChar("Brock", center)
    mod, restore = load_with_fake_evennia([DummySession(caller), DummySession(misty), DummySession(brock)])

    try:
        message = call_where(mod, caller, "#roomprivate")
        output = call_where(mod, brock)
    finally:
        restore()

    assert message == "This room is now hidden from +where."
    assert "Misty" in output
    assert "*Private*" in output
    assert "Town Square" not in output
    assert "Pokemon Center" in output


def test_where_rejects_unimplemented_legacy_filters():
    town = DummyRoom("Town Square")
    caller = DummyChar("Ash", town)
    mod, restore = load_with_fake_evennia([DummySession(caller)])

    try:
        output = call_where(mod, caller, "#active")
    finally:
        restore()

    assert output == "Unknown +where option. Use +where #help for usage."


def test_where_target_lookup_shows_one_online_character():
    town = DummyRoom("Town Square")
    center = DummyRoom("Pokemon Center")
    caller = DummyChar("Ash", town)
    misty = DummyChar("Misty", center)
    brock = DummyChar("Brock", center)
    mod, restore = load_with_fake_evennia([DummySession(caller), DummySession(misty), DummySession(brock)])

    try:
        output = call_where(mod, caller, "Mis")
    finally:
        restore()

    assert "Misty" in output
    assert "Pokemon Center" in output
    assert "Brock" not in output

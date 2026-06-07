import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def load_cmd_module(sessions=None):
    names = (
        "evennia",
        "evennia.objects",
        "evennia.objects.objects",
        "evennia.utils",
        "evennia.utils.evtable",
        "evennia.utils.utils",
        "evennia.commands",
        "evennia.commands.default",
        "evennia.commands.default.account",
        "commands.player.cmd_where",
    )
    originals = {name: sys.modules.get(name) for name in names}

    class FakeSessionHandler:
        def get_sessions(self):
            return list(sessions or [])

    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    fake_evennia.SESSION_HANDLER = FakeSessionHandler()
    fake_commands = types.ModuleType("evennia.commands")
    fake_default = types.ModuleType("evennia.commands.default")
    fake_account = types.ModuleType("evennia.commands.default.account")

    fake_obj_mod = types.ModuleType("evennia.objects.objects")
    fake_obj_mod.DefaultCharacter = type("DefaultCharacter", (), {})
    fake_objects_pkg = types.ModuleType("evennia.objects")
    fake_objects_pkg.objects = fake_obj_mod
    sys.modules["evennia.objects"] = fake_objects_pkg
    sys.modules["evennia.objects.objects"] = fake_obj_mod

    class FakeColumn:
        def __init__(self):
            self.options = {}

    class FakeTable:
        def __init__(self, args, kwargs):
            self.args = args
            self.kwargs = kwargs
            self.table = [FakeColumn() for _ in args]

    class FakeDefaultCmdWho:
        client_width_value = 78

        def client_width(self):
            return self.client_width_value

        def styled_table(self, *args, **kwargs):
            return FakeTable(args, kwargs)

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
    fake_utils_utils_mod = types.ModuleType("evennia.utils.utils")
    fake_utils_utils_mod.time_format = lambda sec, digits=1: f"{int(sec)}s"
    fake_utils_pkg = types.ModuleType("evennia.utils")
    fake_utils_pkg.evtable = fake_evtable_mod
    fake_utils_pkg.utils = fake_utils_utils_mod

    fake_account.CmdWho = FakeDefaultCmdWho
    sys.modules["evennia"] = fake_evennia
    sys.modules["evennia.utils"] = fake_utils_pkg
    sys.modules["evennia.utils.evtable"] = fake_evtable_mod
    sys.modules["evennia.utils.utils"] = fake_utils_utils_mod
    sys.modules["evennia.commands"] = fake_commands
    sys.modules["evennia.commands.default"] = fake_default
    sys.modules["evennia.commands.default.account"] = fake_account

    path = os.path.join(ROOT, "commands", "player", "cmd_who.py")
    spec = importlib.util.spec_from_file_location("commands.player.cmd_who", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

    def restore():
        sys.modules.pop("commands.player.cmd_who", None)
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
    def __init__(self, key, room=None, gender="Unknown", idle=0, account_name=None):
        self.key = key
        self.name = key
        self.id = hash(key)
        self.location = room
        self.db = types.SimpleNamespace(gender=gender)
        self.idle_time = idle
        self.messages = []
        self.account = types.SimpleNamespace(key=account_name or f"{key}Account")

    def is_typeclass(self, *args, **kwargs):
        return True

    def msg(self, text):
        self.messages.append(text)

    def check_permstring(self, _perm):
        return False


def test_who_table_width_uses_wider_floor_and_caps_large_clients():
    mod, restore = load_cmd_module()
    try:
        assert mod.get_who_table_width(78) == 100
        assert mod.get_who_table_width(120) == 120
        assert mod.get_who_table_width(200) == 140
        assert mod.get_who_table_width("bad") == 100
    finally:
        restore()


def test_privileged_who_table_gets_width_budget():
    mod, restore = load_cmd_module()
    try:
        cmd = mod.CmdStaffWho()
        cmd.client_width_value = 128
        result = cmd.styled_table("a", "b", "c", "d", "e", "f", "g", "h")
        assert result.kwargs["width"] == 128
        assert [column.options["width"] for column in result.table] == [24, 12, 9, 21, 25, 9, 12, 16]
    finally:
        restore()


def test_short_who_table_keeps_default_width_behavior():
    mod, restore = load_cmd_module()
    try:
        cmd = mod.CmdStaffWho()
        result = cmd.styled_table("a", "b", "c")
        assert "width" not in result.kwargs
        assert all("width" not in column.options for column in result.table)
    finally:
        restore()


def test_who_column_widths_keep_idle_and_cmds_compact():
    mod, restore = load_cmd_module()
    try:
        widths = mod.get_who_column_widths(120)
        assert widths == (21, 12, 9, 18, 23, 9, 12, 16)
        assert sum(widths) == 120
    finally:
        restore()


def test_staff_who_is_at_command_with_staff_lock():
    mod, restore = load_cmd_module()
    try:
        assert mod.CmdStaffWho.key == "@who"
        assert "staffwho" in mod.CmdStaffWho.aliases
        assert "perm(Admin)" in mod.CmdStaffWho.locks
    finally:
        restore()


def test_player_who_lists_puppets_not_accounts():
    town = DummyRoom("Town Square")
    caller = DummyChar("Yang", town, gender="M", idle=12, account_name="rootadmin")
    other = DummyChar("Test2", town, gender="F", idle=30, account_name="otheracct")
    mod, restore = load_cmd_module([DummySession(caller), DummySession(other)])
    try:
        cmd = mod.CmdWho()
        cmd.caller = caller
        cmd.args = ""
        cmd.func()
        output = caller.messages[-1]
    finally:
        restore()

    assert "Yang" in output
    assert "Test2" in output
    assert "Town Square" in output
    assert "rootadmin" not in output
    assert "otheracct" not in output
    assert "'cols': ('|cName|n', '|cIC|n', '|cIdle|n', '|cSex|n', '|cLocation|n')" in output
    assert "|cYang|n" in output
    assert "|gTown Square|n" in output


def test_player_who_exposes_pf1_alias():
    mod, restore = load_cmd_module()
    try:
        assert mod.CmdWho.key == "who"
        assert "3who" in mod.CmdWho.aliases
    finally:
        restore()

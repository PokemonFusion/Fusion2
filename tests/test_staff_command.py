import importlib.util
import os
import sys
import types


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module(accounts=None, sessions=None):
    originals = {name: sys.modules.get(name) for name in (
        "evennia",
        "evennia.accounts",
        "evennia.accounts.models",
        "evennia.utils",
        "evennia.utils.evtable",
    )}

    class FakeSessionHandler:
        def get_sessions(self):
            return list(sessions or [])

    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    fake_evennia.SESSION_HANDLER = FakeSessionHandler()
    sys.modules["evennia"] = fake_evennia

    class FakeObjects:
        @staticmethod
        def all():
            return list(accounts or [])

    class FakeAccountDB:
        objects = FakeObjects()

    fake_models = types.ModuleType("evennia.accounts.models")
    fake_models.AccountDB = FakeAccountDB
    fake_accounts = types.ModuleType("evennia.accounts")
    fake_accounts.models = fake_models
    sys.modules["evennia.accounts"] = fake_accounts
    sys.modules["evennia.accounts.models"] = fake_models

    class FakeEvTable:
        def __init__(self, *cols):
            self.rows = []

        def add_row(self, *vals):
            self.rows.append(vals)

        def __str__(self):
            return repr(self.rows)

    fake_evtable = types.ModuleType("evennia.utils.evtable")
    fake_evtable.EvTable = FakeEvTable
    fake_utils = types.ModuleType("evennia.utils")
    fake_utils.evtable = fake_evtable
    sys.modules["evennia.utils"] = fake_utils
    sys.modules["evennia.utils.evtable"] = fake_evtable

    path = os.path.join(ROOT, "commands", "player", "cmd_staff.py")
    spec = importlib.util.spec_from_file_location("commands.player.cmd_staff", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

    def restore():
        sys.modules.pop("commands.player.cmd_staff", None)
        for name, original in originals.items():
            if original is not None:
                sys.modules[name] = original
            else:
                sys.modules.pop(name, None)

    return mod, restore


class FakePermissions:
    def __init__(self, perms):
        self.perms = list(perms)

    def all(self):
        return list(self.perms)


class FakeAccount:
    def __init__(self, key, ident, perms=()):
        self.key = key
        self.id = ident
        self.permissions = FakePermissions(perms)
        self.db = types.SimpleNamespace()
        self.messages = []

    def msg(self, message):
        self.messages.append(message)


class FakeSession:
    def __init__(self, account):
        self.account = account

    def get_account(self):
        return self.account


def call_staff(mod, caller, args="", switches=None):
    cmd = mod.CmdStaff()
    cmd.caller = caller
    cmd.account = caller
    cmd.args = args
    cmd.switches = switches or []
    cmd.func()
    return caller.messages[-1]


def test_staff_command_lists_account_roster():
    admin = FakeAccount("Admin", 1, perms=("Admin",))
    validator = FakeAccount("Validator", 2, perms=("Validator",))
    player = FakeAccount("Player", 3, perms=("Player",))
    mod, restore = load_cmd_module([validator, admin, player], [FakeSession(admin)])

    try:
        output = call_staff(mod, player)
    finally:
        restore()

    assert "Staff Roster" in output
    assert "Admin" in output
    assert "Online" in output
    assert "Validator" in output
    assert "Offline" in output
    assert "Player" not in output


def test_staff_duty_and_note_require_staff_account():
    player = FakeAccount("Player", 1, perms=("Player",))
    mod, restore = load_cmd_module([player], [])

    try:
        output = call_staff(mod, player, switches=["duty"])
    finally:
        restore()

    assert output == "Only staff can change staff roster status."


def test_staff_can_toggle_duty_and_set_note():
    admin = FakeAccount("Admin", 1, perms=("Admin",))
    mod, restore = load_cmd_module([admin], [])

    try:
        duty = call_staff(mod, admin, args="off", switches=["duty"])
        note = call_staff(mod, admin, args="Reviewing apps", switches=["note"])
        roster = call_staff(mod, admin)
        cleared = call_staff(mod, admin, switches=["clear"])
    finally:
        restore()

    assert duty == "Staff duty status is now off."
    assert note == "Staff note set to: Reviewing apps"
    assert "Off duty" in roster
    assert "Reviewing apps" in roster
    assert cleared == "Staff note cleared."

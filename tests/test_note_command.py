import importlib.util
import os
import sys
import types


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module(accounts=None, characters=None):
    originals = {name: sys.modules.get(name) for name in (
        "evennia",
        "evennia.utils",
        "evennia.utils.evtable",
    )}

    def search_account(query, exact=True):
        lowered = (query or "").strip().lower()
        return [account for account in accounts or [] if account.key.lower() == lowered]

    def search_object(query, *args, **kwargs):
        lowered = (query or "").strip().lower()
        return [character for character in characters or [] if character.key.lower() == lowered]

    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    fake_evennia.search_account = search_account
    fake_evennia.search_object = search_object
    sys.modules["evennia"] = fake_evennia

    class FakeEvTable:
        def __init__(self, *cols):
            self.cols = cols
            self.rows = []

        def add_row(self, *vals):
            self.rows.append(vals)

        def __str__(self):
            return repr((self.cols, self.rows))

    fake_evtable = types.ModuleType("evennia.utils.evtable")
    fake_evtable.EvTable = FakeEvTable
    fake_utils = types.ModuleType("evennia.utils")
    fake_utils.evtable = fake_evtable
    sys.modules["evennia.utils"] = fake_utils
    sys.modules["evennia.utils.evtable"] = fake_evtable

    path = os.path.join(ROOT, "commands", "player", "cmd_note.py")
    spec = importlib.util.spec_from_file_location("commands.player.cmd_note", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

    def restore():
        sys.modules.pop("commands.player.cmd_note", None)
        for name, original in originals.items():
            if original is not None:
                sys.modules[name] = original
            else:
                sys.modules.pop(name, None)

    return mod, restore


class FakePermissions:
    def __init__(self, perms=()):
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


class FakeCharacter:
    def __init__(self, key, ident):
        self.key = key
        self.id = ident
        self.db = types.SimpleNamespace()

    def is_typeclass(self, path, exact=False):
        return path == "typeclasses.characters.Character"


def call_note(mod, caller, args="", switches=None, lhs="", rhs=""):
    cmd = mod.CmdNote()
    cmd.caller = caller
    cmd.account = caller
    cmd.args = args
    cmd.switches = switches or []
    cmd.lhs = lhs
    cmd.rhs = rhs
    cmd.func()
    return caller.messages[-1]


def test_note_command_requires_staff():
    player = FakeAccount("Player", 1, perms=("Player",))
    mod, restore = load_cmd_module(accounts=[player])

    try:
        output = call_note(mod, player, args="*Player")
    finally:
        restore()

    assert output == "Only staff can use staff notes."


def test_note_command_adds_lists_shows_and_deletes_account_note():
    staff = FakeAccount("Staff", 1, perms=("Helper",))
    target = FakeAccount("Player", 2)
    mod, restore = load_cmd_module(accounts=[staff, target])

    try:
        added = call_note(mod, staff, switches=["add"], lhs="*Player", rhs="Watch validation status.")
        listed = call_note(mod, staff, args="*Player")
        shown = call_note(mod, staff, switches=["show"], lhs="*Player", rhs="1")
        deleted = call_note(mod, staff, switches=["del"], lhs="*Player", rhs="1")
    finally:
        restore()

    assert added == "Staff note #1 added to account Player."
    assert "Staff Notes for account Player" in listed
    assert "Watch validation status." in shown
    assert deleted == "Staff note #1 removed from account Player."


def test_note_command_can_target_characters_with_prefix():
    staff = FakeAccount("Staff", 1, perms=("Validator",))
    character = FakeCharacter("Misty", 3)
    mod, restore = load_cmd_module(accounts=[staff], characters=[character])

    try:
        added = call_note(mod, staff, switches=["add"], lhs="char:Misty", rhs="Approved starter notes.")
        listed = call_note(mod, staff, args="char:Misty")
    finally:
        restore()

    assert added == "Staff note #1 added to character Misty."
    assert "Approved starter notes." in listed


def test_note_command_reports_ambiguous_account_and_character_names():
    staff = FakeAccount("Staff", 1, perms=("Admin",))
    account = FakeAccount("Echo", 2)
    character = FakeCharacter("Echo", 3)
    mod, restore = load_cmd_module(accounts=[staff, account], characters=[character])

    try:
        output = call_note(mod, staff, args="Echo")
    finally:
        restore()

    assert "Multiple targets match" in output
    assert "account Echo" in output
    assert "character Echo" in output

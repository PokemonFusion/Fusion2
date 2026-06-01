import importlib.util
import os
import sys
import types

import pytest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


class FakeConfigObjects:
    def __init__(self):
        self.values = {}

    def conf(self, key, value=None, default=None, delete=False):
        if delete:
            self.values.pop(key, None)
            return None
        if value is not None:
            self.values[key] = value
            return value
        return self.values.get(key, default)


class FakeServerConfig:
    objects = FakeConfigObjects()


def load_cmd_module():
    originals = {name: sys.modules.get(name) for name in (
        "evennia",
        "evennia.utils",
        "evennia.utils.evtable",
    )}

    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
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

    path = os.path.join(ROOT, "commands", "player", "cmd_request.py")
    spec = importlib.util.spec_from_file_location("commands.player.cmd_request", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    mod.support_requests._server_config = lambda: FakeServerConfig

    def restore():
        sys.modules.pop("commands.player.cmd_request", None)
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


class FakeLocation:
    key = "Lobby"


class FakeCharacter:
    key = "Tester"
    id = 99
    location = FakeLocation()


class FakeSession:
    def __init__(self, puppet=None):
        self.puppet = puppet

    def get_puppet(self):
        return self.puppet


@pytest.fixture(autouse=True)
def fake_config():
    FakeServerConfig.objects = FakeConfigObjects()


def call_request(mod, caller, args="", switches=None, puppet=None):
    cmd = mod.CmdRequest()
    cmd.caller = caller
    cmd.account = caller
    cmd.obj = caller
    cmd.session = FakeSession(puppet)
    cmd.args = args
    cmd.switches = switches or []
    cmd.func()
    return caller.messages[-1]


def test_request_command_submits_account_request_with_character_context():
    mod, restore = load_cmd_module()
    player = FakeAccount("Player", 1)

    try:
        output = call_request(mod, player, "I am stuck in chargen.", puppet=FakeCharacter())
        stored = mod.support_requests.get_request(1)
    finally:
        restore()

    assert output == "Request #1 submitted. Staff will review it when available."
    assert stored["requester_account"] == "Player"
    assert stored["requester_character"] == "Tester"
    assert stored["location"] == "Lobby"


def test_request_command_lists_shows_and_closes_own_requests():
    mod, restore = load_cmd_module()
    player = FakeAccount("Player", 1)

    try:
        call_request(mod, player, "Please review my profile.")
        listing = call_request(mod, player, switches=["list"])
        shown = call_request(mod, player, args="1", switches=["show"])
        closed = call_request(mod, player, args="1 fixed", switches=["close"])
    finally:
        restore()

    assert "Your Support Requests" in listing
    assert "Please review my profile." in shown
    assert closed == "Request #1 closed."


def test_request_queue_and_claim_are_staff_only():
    mod, restore = load_cmd_module()
    player = FakeAccount("Player", 1)
    staff = FakeAccount("Staff", 2, perms=("Helper",))

    try:
        call_request(mod, player, "Need help.")
        denied = call_request(mod, player, switches=["queue"])
        queue = call_request(mod, staff, switches=["queue"])
        claimed = call_request(mod, staff, args="1", switches=["claim"])
    finally:
        restore()

    assert denied == "Only staff can view the support request queue."
    assert "Support Request Queue" in queue
    assert "Player" in queue
    assert claimed == "Request #1 claimed."

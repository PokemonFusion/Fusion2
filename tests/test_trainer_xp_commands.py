import importlib
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_command_modules(monkeypatch):
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    monkeypatch.setitem(sys.modules, "evennia", fake_evennia)
    for name in ("commands.player.cmd_trainer_xp", "commands.admin.cmd_trainer_xp"):
        sys.modules.pop(name, None)
    player_mod = importlib.import_module("commands.player.cmd_trainer_xp")
    admin_mod = importlib.import_module("commands.admin.cmd_trainer_xp")
    return player_mod, admin_mod


class DummyCharacter:
    def __init__(self, key="Target", *, txp=0, is_char=True):
        self.key = key
        self.db = types.SimpleNamespace(txp=txp)
        self.is_char = is_char
        self.messages: list[str] = []

    def is_typeclass(self, _path, exact=False):
        return self.is_char

    def msg(self, text):
        self.messages.append(text)


class DummyCaller(DummyCharacter):
    def __init__(self, target):
        super().__init__("Caller")
        self.target = target

    def search(self, text, global_search=True):
        return self.target if text == self.target.key else None


def test_player_txp_command_displays_status(monkeypatch):
    player_mod, _admin_mod = load_command_modules(monkeypatch)
    caller = DummyCharacter(txp=40)
    cmd = player_mod.CmdTrainerXP()
    cmd.caller = caller

    cmd.func()

    assert caller.messages
    assert "Trainer Level" in caller.messages[-1]
    assert "TXP" in caller.messages[-1]
    assert "40" in caller.messages[-1]


def test_admin_txp_command_adjusts_and_sets(monkeypatch):
    _player_mod, admin_mod = load_command_modules(monkeypatch)
    target = DummyCharacter(txp=10)
    caller = DummyCaller(target)

    add_cmd = admin_mod.CmdAdminTrainerXP()
    add_cmd.caller = caller
    add_cmd.cmdstring = "@txp/add"
    add_cmd.args = "Target=25"
    add_cmd.parse()
    add_cmd.func()

    assert target.db.trainer_xp == 35
    assert target.db.txp == 35
    assert "adjusted to 35" in caller.messages[-1]

    set_cmd = admin_mod.CmdAdminTrainerXP()
    set_cmd.caller = caller
    set_cmd.cmdstring = "@txp/set"
    set_cmd.args = "Target=5"
    set_cmd.parse()
    set_cmd.func()

    assert target.db.trainer_xp == 5
    assert target.db.txp == 5
    assert "set to 5" in caller.messages[-1]


def test_admin_txp_command_is_staff_only(monkeypatch):
    _player_mod, admin_mod = load_command_modules(monkeypatch)

    assert admin_mod.CmdAdminTrainerXP.locks == "cmd:perm(Builder)"

import importlib.util
import os
import re
import sys
import types


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module():
    module_names = [
        "evennia",
        "evennia.commands",
        "evennia.commands.default",
        "evennia.commands.default.account",
        "evennia.utils",
    ]
    originals = {name: sys.modules.get(name) for name in module_names}

    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})

    fake_commands = types.ModuleType("evennia.commands")
    fake_default = types.ModuleType("evennia.commands.default")
    fake_account = types.ModuleType("evennia.commands.default.account")
    fake_account.CmdIC = type("CmdIC", (), {})
    fake_account.CmdOOC = type("CmdOOC", (), {})

    fake_utils = types.ModuleType("evennia.utils")
    fake_utils.logger = types.SimpleNamespace(log_sec=lambda *args, **kwargs: None)

    sys.modules["evennia"] = fake_evennia
    sys.modules["evennia.commands"] = fake_commands
    sys.modules["evennia.commands.default"] = fake_default
    sys.modules["evennia.commands.default.account"] = fake_account
    sys.modules["evennia.utils"] = fake_utils

    path = os.path.join(ROOT, "commands", "player", "cmd_roleplay.py")
    spec = importlib.util.spec_from_file_location("commands.player.cmd_roleplay", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        for name, original in originals.items():
            if original is not None:
                sys.modules[name] = original
            else:
                sys.modules.pop(name, None)
    return mod


class DummyRoom:
    def __init__(self):
        self.messages = []

    def msg_contents(self, text, from_obj=None):
        self.messages.append((text, from_obj))


class DummyCaller:
    def __init__(self, name="Character", location=None):
        self.name = name
        self.location = location
        self.messages = []

    def at_pre_say(self, speech):
        return speech

    def msg(self, text):
        self.messages.append(text)


def test_ooc_requires_space_or_exact_command_match():
    mod = load_cmd_module()
    arg_regex = re.compile(mod.CmdOOC.arg_regex)

    assert arg_regex.match("")
    assert arg_regex.match(" hey")
    assert not arg_regex.match("hey")
    assert not arg_regex.match(":shrug")


def test_ooc_speech_strips_parser_separator():
    mod = load_cmd_module()
    room = DummyRoom()
    caller = DummyCaller(location=room)

    cmd = mod.CmdOOC()
    cmd.caller = caller
    cmd.args = " hey"
    cmd.func()

    assert room.messages == [
        ('|w<OOC>|n |GCharacter says, "hey"|n', caller),
    ]


def test_ooc_pose_strips_parser_separator():
    mod = load_cmd_module()
    room = DummyRoom()
    caller = DummyCaller(location=room)

    cmd = mod.CmdOOC()
    cmd.caller = caller
    cmd.args = " :shrug"
    cmd.func()

    assert room.messages == [
        ("|w<OOC>|n |GCharacter shrug|n", caller),
    ]

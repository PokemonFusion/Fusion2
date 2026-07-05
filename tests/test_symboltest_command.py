import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_symbol_module(enabled=True):
    patched = {
        "evennia": sys.modules.get("evennia"),
        "evennia.commands": sys.modules.get("evennia.commands"),
        "evennia.commands.command": sys.modules.get("evennia.commands.command"),
    }
    try:
        fake_evennia = types.ModuleType("evennia")
        fake_commands = types.ModuleType("evennia.commands")
        fake_command = types.ModuleType("evennia.commands.command")
        fake_command.Command = type("Command", (), {})
        fake_commands.command = fake_command
        fake_evennia.commands = fake_commands
        sys.modules["evennia"] = fake_evennia
        sys.modules["evennia.commands"] = fake_commands
        sys.modules["evennia.commands.command"] = fake_command

        path = os.path.join(ROOT, "commands", "player", "cmd_symboltest.py")
        spec = importlib.util.spec_from_file_location("commands.player.cmd_symboltest", path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)

        def command_enabled(caller=None):
            return enabled

        def require_access(caller):
            if command_enabled(caller):
                return True
            caller.msg("Symbol diagnostics are not available right now.")
            return False

        mod.symbol_test_command_enabled = command_enabled
        mod._require_symbol_test_access = require_access
        return mod
    finally:
        for name, module in patched.items():
            if module is not None:
                sys.modules[name] = module
            else:
                sys.modules.pop(name, None)


def load_ui_cmdset(symbol_enabled):
    patched = {
        "evennia": sys.modules.get("evennia"),
        "commands.player.cmd_battleuistyle": sys.modules.get("commands.player.cmd_battleuistyle"),
        "commands.player.cmd_symboltest": sys.modules.get("commands.player.cmd_symboltest"),
        "commands.player.cmd_uimode": sys.modules.get("commands.player.cmd_uimode"),
        "commands.player.cmd_uitheme": sys.modules.get("commands.player.cmd_uitheme"),
    }
    try:
        class FakeCmdSet:
            def __init__(self):
                self.added = []

            def add(self, command):
                self.added.append(command)

        fake_evennia = types.ModuleType("evennia")
        fake_evennia.CmdSet = FakeCmdSet
        sys.modules["evennia"] = fake_evennia

        def command_class(key):
            return type("Command", (), {"key": key})

        fake_battle_ui = types.ModuleType("commands.player.cmd_battleuistyle")
        fake_battle_ui.CmdBattleUiStyle = command_class("+battleui")
        sys.modules["commands.player.cmd_battleuistyle"] = fake_battle_ui

        fake_symbol = types.ModuleType("commands.player.cmd_symboltest")
        fake_symbol.CmdSymbolTest = command_class("+symboltest")
        fake_symbol.symbol_test_command_enabled = lambda: symbol_enabled
        sys.modules["commands.player.cmd_symboltest"] = fake_symbol

        fake_uimode = types.ModuleType("commands.player.cmd_uimode")
        fake_uimode.CmdUiMode = command_class("+uimode")
        sys.modules["commands.player.cmd_uimode"] = fake_uimode

        fake_uitheme = types.ModuleType("commands.player.cmd_uitheme")
        fake_uitheme.CmdUiTheme = command_class("+uitheme")
        sys.modules["commands.player.cmd_uitheme"] = fake_uitheme

        path = os.path.join(ROOT, "commands", "cmdsets", "ui.py")
        spec = importlib.util.spec_from_file_location("commands.cmdsets.ui", path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        return mod
    finally:
        for name, module in patched.items():
            if module is not None:
                sys.modules[name] = module
            else:
                sys.modules.pop(name, None)


class DummyCaller:
    def __init__(self):
        self.msgs = []

    def msg(self, text):
        self.msgs.append(text)


def test_symboltest_blocks_normal_player_when_gate_disabled():
    mod = load_symbol_module(enabled=False)
    caller = DummyCaller()

    cmd = mod.CmdSymbolTest()
    cmd.caller = caller
    cmd.args = "ui"
    cmd.func()

    assert caller.msgs == ["Symbol diagnostics are not available right now."]


def test_symboltest_renders_when_gate_enabled():
    mod = load_symbol_module(enabled=True)
    caller = DummyCaller()

    cmd = mod.CmdSymbolTest()
    cmd.caller = caller
    cmd.args = "ascii"
    cmd.func()

    assert "Printable ASCII 32-126" in caller.msgs[-1]


def test_ui_cmdset_does_not_register_symboltest_when_gate_disabled():
    mod = load_ui_cmdset(symbol_enabled=False)

    cmdset = mod.UiCmdSet()
    cmdset.at_cmdset_creation()

    assert "+symboltest" not in [command.key for command in cmdset.added]


def test_ui_cmdset_registers_symboltest_when_gate_enabled():
    mod = load_ui_cmdset(symbol_enabled=True)

    cmdset = mod.UiCmdSet()
    cmdset.at_cmdset_creation()

    assert "+symboltest" in [command.key for command in cmdset.added]

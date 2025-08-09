import os
import sys
import types
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module():
    path = os.path.join(ROOT, "commands", "cmd_uitheme.py")
    spec = importlib.util.spec_from_file_location("commands.cmd_uitheme", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def setup_module():
    global orig_evennia
    orig_evennia = sys.modules.get("evennia")
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    sys.modules["evennia"] = fake_evennia


def teardown_module():
    if orig_evennia is not None:
        sys.modules["evennia"] = orig_evennia
    else:
        sys.modules.pop("evennia", None)


def test_uitheme_sets_theme():
    cmd_mod = load_cmd_module()
    caller = types.SimpleNamespace(db=types.SimpleNamespace(ui_theme="green"), msgs=[])
    caller.msg = lambda text: caller.msgs.append(text)
    cmd = cmd_mod.CmdUiTheme()
    cmd.caller = caller
    cmd.args = "blue"
    cmd.func()
    assert caller.db.ui_theme == "blue"
    assert caller.msgs[-1] == "UI theme set to blue."


def test_uitheme_shows_current():
    cmd_mod = load_cmd_module()
    caller = types.SimpleNamespace(db=types.SimpleNamespace(ui_theme="cyan"), msgs=[])
    caller.msg = lambda text: caller.msgs.append(text)
    cmd = cmd_mod.CmdUiTheme()
    cmd.caller = caller
    cmd.args = ""
    cmd.func()
    assert caller.msgs[-1] == "Current UI theme: cyan."


def test_uitheme_invalid():
    cmd_mod = load_cmd_module()
    caller = types.SimpleNamespace(db=types.SimpleNamespace(), msgs=[])
    caller.msg = lambda text: caller.msgs.append(text)
    cmd = cmd_mod.CmdUiTheme()
    cmd.caller = caller
    cmd.args = "orange"
    cmd.func()
    assert "Usage" in caller.msgs[-1]

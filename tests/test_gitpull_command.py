import os
import sys
import types
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module():
    path = os.path.join(ROOT, "commands", "cmd_gitpull.py")
    spec = importlib.util.spec_from_file_location("commands.cmd_gitpull", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_gitpull_success_message():
    orig_subprocess = sys.modules.get("subprocess")
    fake_subprocess = types.ModuleType("subprocess")

    class Result:
        def __init__(self):
            self.stdout = "Already up to date."
            self.stderr = ""
            self.returncode = 0

    fake_subprocess.run = lambda *a, **k: Result()
    sys.modules["subprocess"] = fake_subprocess

    orig_evennia = sys.modules.get("evennia")
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    sys.modules["evennia"] = fake_evennia

    cmd_mod = load_cmd_module()

    class DummyCaller:
        def __init__(self):
            self.msgs = []

        def msg(self, text):
            self.msgs.append(text)

    caller = DummyCaller()
    cmd = cmd_mod.CmdGitPull()
    cmd.caller = caller
    cmd.func()

    if orig_subprocess is not None:
        sys.modules["subprocess"] = orig_subprocess
    else:
        sys.modules.pop("subprocess", None)
    if orig_evennia is not None:
        sys.modules["evennia"] = orig_evennia
    else:
        sys.modules.pop("evennia", None)

    assert caller.msgs
    assert caller.msgs[0].lower().startswith("running git pull")
    assert any("completed" in m.lower() for m in caller.msgs)


def test_gitpull_failure_message():
    orig_subprocess = sys.modules.get("subprocess")
    fake_subprocess = types.ModuleType("subprocess")

    class Result:
        def __init__(self):
            self.stdout = ""
            self.stderr = "fatal: not a git repository"
            self.returncode = 1

    fake_subprocess.run = lambda *a, **k: Result()
    sys.modules["subprocess"] = fake_subprocess

    orig_evennia = sys.modules.get("evennia")
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    sys.modules["evennia"] = fake_evennia

    cmd_mod = load_cmd_module()

    class DummyCaller:
        def __init__(self):
            self.msgs = []

        def msg(self, text):
            self.msgs.append(text)

    caller = DummyCaller()
    cmd = cmd_mod.CmdGitPull()
    cmd.caller = caller
    cmd.func()

    if orig_subprocess is not None:
        sys.modules["subprocess"] = orig_subprocess
    else:
        sys.modules.pop("subprocess", None)
    if orig_evennia is not None:
        sys.modules["evennia"] = orig_evennia
    else:
        sys.modules.pop("evennia", None)

    assert caller.msgs
    assert caller.msgs[0].lower().startswith("running git pull")
    last = caller.msgs[-1].lower()
    assert "failed" in last and "fatal" in last

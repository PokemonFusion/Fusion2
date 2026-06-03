import importlib.util
import os
import sys
import types

from utils import landing_announcement

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module():
    original = sys.modules.get("evennia")
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    sys.modules["evennia"] = fake_evennia

    path = os.path.join(ROOT, "commands", "admin", "cmd_landingnote.py")
    spec = importlib.util.spec_from_file_location("commands.admin.cmd_landingnote", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

    def restore():
        sys.modules.pop("commands.admin.cmd_landingnote", None)
        if original is not None:
            sys.modules["evennia"] = original
        else:
            sys.modules.pop("evennia", None)

    return mod, restore


class FakeConfigManager:
    def __init__(self):
        self.data = {}

    def conf(self, key=None, value=None, delete=False, default=None):
        if delete:
            self.data.pop(key, None)
            return None
        if value is not None:
            self.data[key] = value
            return None
        return self.data.get(key, default() if callable(default) else default)


class FakeServerConfig:
    objects = FakeConfigManager()


class DummyCaller:
    key = "Wizard"

    def __init__(self):
        self.msgs = []

    def msg(self, text):
        self.msgs.append(text)


def call_landingnote(mod, caller, args="", switches=None):
    cmd = mod.CmdLandingNote()
    cmd.caller = caller
    cmd.args = args
    cmd.switches = switches or []
    cmd.func()
    return caller.msgs[-1]


def test_landingnote_is_wizard_locked():
    mod, restore = load_cmd_module()
    try:
        assert mod.CmdLandingNote.locks == "cmd:perm(Wizards)"
    finally:
        restore()


def test_landingnote_view_and_edit_flow(monkeypatch):
    FakeServerConfig.objects = FakeConfigManager()
    monkeypatch.setattr(landing_announcement, "_server_config", lambda: FakeServerConfig)
    mod, restore = load_cmd_module()
    caller = DummyCaller()

    try:
        current = call_landingnote(mod, caller, switches=["view"])
        title = call_landingnote(mod, caller, args="Launch Notes", switches=["title"])
        body = call_landingnote(mod, caller, args="Testing routes and battles.", switches=["body"])
        bullet = call_landingnote(mod, caller, args="Try the webclient.", switches=["bullet"])
        hidden = call_landingnote(mod, caller, switches=["hide"])
        shown = call_landingnote(mod, caller, switches=["show"])
        cleared = call_landingnote(mod, caller, switches=["clearbullets"])
        reset = call_landingnote(mod, caller, switches=["reset"])
    finally:
        restore()

    assert "Development Server Notes" in current
    assert title == "Landing announcement title set to: Launch Notes"
    assert body == "Landing announcement body updated."
    assert bullet == "Landing announcement bullet #4 added."
    assert hidden == "Landing announcement is now hidden."
    assert shown == "Landing announcement is now visible."
    assert cleared == "Landing announcement bullets cleared."
    assert reset == "Landing announcement reset to defaults."
    assert landing_announcement.get_landing_announcement().is_default is True


def test_landingnote_requires_text_for_text_switches(monkeypatch):
    FakeServerConfig.objects = FakeConfigManager()
    monkeypatch.setattr(landing_announcement, "_server_config", lambda: FakeServerConfig)
    mod, restore = load_cmd_module()
    caller = DummyCaller()

    try:
        output = call_landingnote(mod, caller, switches=["title"])
    finally:
        restore()

    assert output == "Usage: @landingnote/title <text>"

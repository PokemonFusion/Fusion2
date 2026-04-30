import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module():
    path = os.path.join(ROOT, "commands", "admin", "cmd_sitestatus.py")
    spec = importlib.util.spec_from_file_location("commands.admin.cmd_sitestatus", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class DummyCaller:
    def __init__(self):
        self.msgs = []

    def msg(self, text):
        self.msgs.append(text)


class DummyStatus:
    def __init__(self, status="open", label="Open", message="The world is ready.", logins_enabled=True):
        self.status = status
        self.label = label
        self.message = message
        self.css_class = status
        self.logins_enabled = logins_enabled


def with_fake_evennia():
    orig_evennia = sys.modules.get("evennia")
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    sys.modules["evennia"] = fake_evennia
    return orig_evennia


def restore_evennia(orig_evennia):
    if orig_evennia is not None:
        sys.modules["evennia"] = orig_evennia
    else:
        sys.modules.pop("evennia", None)


def test_sitestatus_displays_current_status():
    orig_evennia = with_fake_evennia()
    cmd_mod = load_cmd_module()
    cmd_mod.get_site_status = lambda: DummyStatus(status="limited", label="Limited", message="Testing.", logins_enabled=True)

    cmd = cmd_mod.CmdSiteStatus()
    cmd.caller = DummyCaller()
    cmd.args = ""
    cmd.parse()
    cmd.func()

    restore_evennia(orig_evennia)

    assert cmd.caller.msgs
    assert "Limited" in cmd.caller.msgs[0]
    assert "Testing." in cmd.caller.msgs[0]


def test_sitestatus_sets_maintenance_with_message():
    orig_evennia = with_fake_evennia()
    cmd_mod = load_cmd_module()
    calls = []

    def fake_set(status, message=None, changed_by=None):
        calls.append((status, message, changed_by))
        return DummyStatus(status=status, label="Maintenance", message=message, logins_enabled=False)

    cmd_mod.set_site_status = fake_set

    cmd = cmd_mod.CmdSiteStatus()
    cmd.caller = DummyCaller()
    cmd.args = "maintenance = Testing updates"
    cmd.parse()
    cmd.func()

    restore_evennia(orig_evennia)

    assert calls == [("maintenance", "Testing updates", cmd.caller)]
    assert "Maintenance" in cmd.caller.msgs[-1]
    assert "Testing updates" in cmd.caller.msgs[-1]


def test_sitestatus_clear_resets_status():
    orig_evennia = with_fake_evennia()
    cmd_mod = load_cmd_module()
    called = []

    def fake_clear():
        called.append(True)
        return DummyStatus()

    cmd_mod.clear_site_status = fake_clear

    cmd = cmd_mod.CmdSiteStatus()
    cmd.caller = DummyCaller()
    cmd.args = "clear"
    cmd.parse()
    cmd.func()

    restore_evennia(orig_evennia)

    assert called
    assert "reset" in cmd.caller.msgs[-1].lower()


def test_sitestatus_rejects_invalid_status_without_mutation():
    orig_evennia = with_fake_evennia()
    cmd_mod = load_cmd_module()
    calls = []
    cmd_mod.set_site_status = lambda *args, **kwargs: calls.append((args, kwargs))

    cmd = cmd_mod.CmdSiteStatus()
    cmd.caller = DummyCaller()
    cmd.args = "offline"
    cmd.parse()
    cmd.func()

    restore_evennia(orig_evennia)

    assert not calls
    assert "unknown" in cmd.caller.msgs[-1].lower()

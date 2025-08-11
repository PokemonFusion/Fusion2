import os
import sys
import types
import importlib.util
import logging

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module():
    path = os.path.join(ROOT, "commands", "debug", "cmd_debugpy.py")
    spec = importlib.util.spec_from_file_location("commands.debug.cmd_debugpy", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_debugpy_logs_connection(caplog):
    orig_django_conf = sys.modules.get("django.conf")
    fake_django_conf = types.ModuleType("django.conf")
    fake_django_conf.settings = types.SimpleNamespace(COMMAND_DEFAULT_CLASS="core")
    sys.modules["django.conf"] = fake_django_conf

    orig_evennia = sys.modules.get("evennia")
    fake_evennia = types.ModuleType("evennia")
    fake_cmd_base = type("Command", (), {})
    fake_utils_sub = types.ModuleType("evennia.utils.utils")
    fake_utils_sub.class_from_module = lambda path: fake_cmd_base
    fake_utils_pkg = types.ModuleType("evennia.utils")
    fake_utils_pkg.utils = fake_utils_sub
    fake_evennia.utils = fake_utils_pkg
    fake_evennia.Command = fake_cmd_base
    sys.modules["evennia"] = fake_evennia
    sys.modules["evennia.utils"] = fake_utils_pkg
    sys.modules["evennia.utils.utils"] = fake_utils_sub

    mod = load_cmd_module()
    fake_debugpy = types.SimpleNamespace(
        listen=lambda *a, **kw: ("127.0.0.1", 5678),
        wait_for_client=lambda: None,
    )
    orig_debugpy = mod.debugpy
    mod.debugpy = fake_debugpy

    caplog.set_level(logging.INFO, logger=mod.__name__)

    cmd = mod.CmdDebugPy()
    cmd.caller = types.SimpleNamespace(msg=lambda t: None)
    list(cmd.func())

    mod.debugpy = orig_debugpy
    if orig_django_conf is not None:
        sys.modules["django.conf"] = orig_django_conf
    else:
        sys.modules.pop("django.conf", None)
    if orig_evennia is not None:
        sys.modules["evennia"] = orig_evennia
    else:
        sys.modules.pop("evennia", None)
    sys.modules.pop("evennia.utils", None)
    sys.modules.pop("evennia.utils.utils", None)

    assert any("debugger connected" in r.message for r in caplog.records)

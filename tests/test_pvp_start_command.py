import os
import sys
import types
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module():
    path = os.path.join(ROOT, "commands", "player", "cmd_pvp.py")
    spec = importlib.util.spec_from_file_location("commands.player.cmd_pvp", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def setup_evennia():
    orig_evennia = sys.modules.get("evennia")
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    utils_mod = types.ModuleType("evennia.utils")
    utils_utils = types.ModuleType("evennia.utils.utils")
    utils_utils.inherits_from = lambda obj, parent: isinstance(obj, parent)
    utils_mod.utils = utils_utils
    fake_evennia.utils = utils_mod
    sys.modules["evennia"] = fake_evennia
    sys.modules["evennia.utils"] = utils_mod
    sys.modules["evennia.utils.utils"] = utils_utils
    return orig_evennia


def restore_evennia(orig_evennia):
    if orig_evennia is not None:
        sys.modules["evennia"] = orig_evennia
    else:
        sys.modules.pop("evennia", None)
    sys.modules.pop("evennia.utils", None)
    sys.modules.pop("evennia.utils.utils", None)


class DummyCaller:
    def __init__(self, pid=1, key="Alice", in_battle=False):
        self.id = pid
        self.key = key
        self.location = object()
        self.msgs = []
        self.ndb = types.SimpleNamespace(battle_instance=(object() if in_battle else None))

    def msg(self, text):
        self.msgs.append(text)


def test_pvpstart_fails_if_host_in_battle():
    orig = setup_evennia()
    cmd_mod = load_cmd_module()

    started = []
    removed = []

    opponent = types.SimpleNamespace(ndb=types.SimpleNamespace(battle_instance=None))
    req = types.SimpleNamespace(opponent_id=2, get_opponent=lambda: opponent)

    def fake_get_requests(loc):
        return {1: req}

    cmd_mod.get_requests, orig_get = fake_get_requests, cmd_mod.get_requests
    cmd_mod.remove_request, orig_remove = lambda c: removed.append(True), cmd_mod.remove_request
    cmd_mod.start_pvp_battle, orig_start = lambda h, o: started.append((h, o)), cmd_mod.start_pvp_battle

    caller = DummyCaller(in_battle=True)
    cmd = cmd_mod.CmdPvpStart()
    cmd.caller = caller
    cmd.func()

    restore_evennia(orig)
    cmd_mod.get_requests = orig_get
    cmd_mod.remove_request = orig_remove
    cmd_mod.start_pvp_battle = orig_start

    assert started == []
    assert caller.msgs and "already engaged" in caller.msgs[-1].lower()


def test_pvpstart_fails_if_opponent_in_battle():
    orig = setup_evennia()
    cmd_mod = load_cmd_module()

    started = []
    removed = []

    opponent = types.SimpleNamespace(ndb=types.SimpleNamespace(battle_instance=object()))
    req = types.SimpleNamespace(opponent_id=2, get_opponent=lambda: opponent)

    def fake_get_requests(loc):
        return {1: req}

    cmd_mod.get_requests, orig_get = fake_get_requests, cmd_mod.get_requests
    cmd_mod.remove_request, orig_remove = lambda c: removed.append(True), cmd_mod.remove_request
    cmd_mod.start_pvp_battle, orig_start = lambda h, o: started.append((h, o)), cmd_mod.start_pvp_battle

    caller = DummyCaller()
    cmd = cmd_mod.CmdPvpStart()
    cmd.caller = caller
    cmd.func()

    restore_evennia(orig)
    cmd_mod.get_requests = orig_get
    cmd_mod.remove_request = orig_remove
    cmd_mod.start_pvp_battle = orig_start

    assert started == []
    assert caller.msgs and "opponent" in caller.msgs[-1].lower()


def test_pvpstart_starts_when_free():
    orig = setup_evennia()
    cmd_mod = load_cmd_module()

    started = []
    removed = []

    opponent = DummyCaller(pid=2, key="Bob")
    req = types.SimpleNamespace(opponent_id=2, get_opponent=lambda: opponent)

    def fake_get_requests(loc):
        return {1: req}

    cmd_mod.get_requests, orig_get = fake_get_requests, cmd_mod.get_requests
    cmd_mod.remove_request, orig_remove = lambda c: removed.append(True), cmd_mod.remove_request
    cmd_mod.start_pvp_battle, orig_start = lambda h, o: started.append((h, o)), cmd_mod.start_pvp_battle

    caller = DummyCaller()
    cmd = cmd_mod.CmdPvpStart()
    cmd.caller = caller
    cmd.func()

    restore_evennia(orig)
    cmd_mod.get_requests = orig_get
    cmd_mod.remove_request = orig_remove
    cmd_mod.start_pvp_battle = orig_start

    assert started and started[0][0] is caller and started[0][1] is opponent
    assert removed
    assert not caller.msgs

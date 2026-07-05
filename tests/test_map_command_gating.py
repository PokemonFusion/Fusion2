import importlib.util
import os
import sys
import types


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _command_class(key):
    return type("FakeCommand", (), {"key": key})


def _install_fake_settings(monkeypatch, *, dev_mode=False, map_enabled=False):
    fake_django = types.ModuleType("django")
    fake_conf = types.ModuleType("django.conf")
    fake_conf.settings = types.SimpleNamespace(
        DEV_MODE=dev_mode,
        MAP_PROTOTYPE_ENABLED=map_enabled,
    )
    fake_django.conf = fake_conf
    monkeypatch.setitem(sys.modules, "django", fake_django)
    monkeypatch.setitem(sys.modules, "django.conf", fake_conf)


def _install_fake_evennia(monkeypatch):
    class FakeCmdSet:
        def __init__(self):
            self.added = []

        def add(self, command):
            self.added.append(command)

    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    fake_evennia.CmdSet = FakeCmdSet
    monkeypatch.setitem(sys.modules, "evennia", fake_evennia)


def _load_cmdstartmap(monkeypatch, *, dev_mode=False, map_enabled=False):
    _install_fake_evennia(monkeypatch)
    _install_fake_settings(monkeypatch, dev_mode=dev_mode, map_enabled=map_enabled)

    calls = []
    fake_maphandler = types.ModuleType("world.maphandler")
    fake_maphandler.create_map_instance = lambda caller: calls.append(caller) or types.SimpleNamespace(key="Map")
    fake_world = types.ModuleType("world")
    fake_world.maphandler = fake_maphandler
    monkeypatch.setitem(sys.modules, "world", fake_world)
    monkeypatch.setitem(sys.modules, "world.maphandler", fake_maphandler)

    path = os.path.join(ROOT, "commands", "player", "cmdstartmap.py")
    spec = importlib.util.spec_from_file_location("commands.player.cmdstartmap", path)
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, mod)
    spec.loader.exec_module(mod)
    return mod, calls


def _load_cmd_map_move(monkeypatch, *, dev_mode=False, map_enabled=False):
    _load_cmdstartmap(monkeypatch, dev_mode=dev_mode, map_enabled=map_enabled)
    path = os.path.join(ROOT, "commands", "player", "cmd_map_move.py")
    spec = importlib.util.spec_from_file_location("commands.player.cmd_map_move", path)
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, mod)
    spec.loader.exec_module(mod)
    return mod


class FakeCaller:
    def __init__(self):
        self.messages = []
        self.location = types.SimpleNamespace(move_entity=self._move_entity)
        self.moves = []

    def msg(self, text):
        self.messages.append(text)

    def _move_entity(self, caller, dx, dy):
        self.moves.append((caller, dx, dy))
        return True


def test_map_start_is_not_usable_when_prototype_gate_disabled(monkeypatch):
    mod, calls = _load_cmdstartmap(monkeypatch, dev_mode=False, map_enabled=False)
    caller = FakeCaller()
    command = mod.CmdStartMap()
    command.caller = caller

    command.func()

    assert calls == []
    assert caller.messages == ["Map prototype commands are not available right now."]


def test_map_move_is_not_usable_when_prototype_gate_disabled(monkeypatch):
    mod = _load_cmd_map_move(monkeypatch, dev_mode=False, map_enabled=False)
    caller = FakeCaller()
    command = mod.CmdMapMove()
    command.caller = caller
    command.args = "n"

    command.func()

    assert caller.moves == []
    assert caller.messages == ["Map prototype commands are not available right now."]


def _load_economy_cmdset(monkeypatch, *, enabled):
    _install_fake_evennia(monkeypatch)
    fake_start = types.ModuleType("commands.player.cmdstartmap")
    fake_start.CmdStartMap = _command_class("+map/start")
    fake_start.map_prototype_enabled = lambda: enabled
    fake_move = types.ModuleType("commands.player.cmd_map_move")
    fake_move.CmdMapMove = _command_class("+map/move")
    fake_store = types.ModuleType("commands.player.cmd_store")
    fake_store.CmdStore = _command_class("+store")
    fake_pokestore = types.ModuleType("commands.player.cmd_pokestore")
    fake_pokestore.CmdPokestore = _command_class("+storage")

    monkeypatch.setitem(sys.modules, "commands.player.cmdstartmap", fake_start)
    monkeypatch.setitem(sys.modules, "commands.player.cmd_map_move", fake_move)
    monkeypatch.setitem(sys.modules, "commands.player.cmd_store", fake_store)
    monkeypatch.setitem(sys.modules, "commands.player.cmd_pokestore", fake_pokestore)

    path = os.path.join(ROOT, "commands", "cmdsets", "economy_map.py")
    spec = importlib.util.spec_from_file_location("commands.cmdsets.economy_map", path)
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, mod)
    spec.loader.exec_module(mod)
    return mod


def _load_map_cmdset(monkeypatch, *, enabled):
    _install_fake_evennia(monkeypatch)
    fake_start = types.ModuleType("commands.player.cmdstartmap")
    fake_start.CmdStartMap = _command_class("+map/start")
    fake_start.map_prototype_enabled = lambda: enabled
    fake_move = types.ModuleType("commands.player.cmd_map_move")
    fake_move.CmdMapMove = _command_class("+map/move")

    monkeypatch.setitem(sys.modules, "commands.player.cmdstartmap", fake_start)
    monkeypatch.setitem(sys.modules, "commands.player.cmd_map_move", fake_move)

    path = os.path.join(ROOT, "commands", "player", "cmdset_map.py")
    spec = importlib.util.spec_from_file_location("commands.player.cmdset_map", path)
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, mod)
    spec.loader.exec_module(mod)
    return mod


def test_default_economy_cmdset_hides_map_commands_when_gate_disabled(monkeypatch):
    mod = _load_economy_cmdset(monkeypatch, enabled=False)

    cmdset = mod.EconomyMapCmdSet()
    cmdset.at_cmdset_creation()

    keys = [command.key for command in cmdset.added]
    assert "+map/start" not in keys
    assert "+map/move" not in keys
    assert keys == ["+store", "+storage"]


def test_default_economy_cmdset_registers_map_commands_when_gate_enabled(monkeypatch):
    mod = _load_economy_cmdset(monkeypatch, enabled=True)

    cmdset = mod.EconomyMapCmdSet()
    cmdset.at_cmdset_creation()

    keys = [command.key for command in cmdset.added]
    assert "+map/start" in keys
    assert "+map/move" in keys


def test_map_cmdset_hides_map_commands_when_gate_disabled(monkeypatch):
    mod = _load_map_cmdset(monkeypatch, enabled=False)

    cmdset = mod.MapCmdSet()
    cmdset.at_cmdset_creation()

    assert cmdset.added == []


def test_map_cmdset_registers_map_commands_when_gate_enabled(monkeypatch):
    mod = _load_map_cmdset(monkeypatch, enabled=True)

    cmdset = mod.MapCmdSet()
    cmdset.at_cmdset_creation()

    keys = [command.key for command in cmdset.added]
    assert keys == ["+map/move", "+map/start"]

import os
import sys
import types
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def test_movesets_invalid_location():
    orig_evennia = sys.modules.get("evennia")
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    sys.modules["evennia"] = fake_evennia

    orig_evmod = sys.modules.get("pokemon.utils.enhanced_evmenu")
    fake_evmod = types.ModuleType("pokemon.utils.enhanced_evmenu")
    class FakeMenu:
        called = False
        def __init__(self, *a, **k):
            FakeMenu.called = True
    fake_evmod.EnhancedEvMenu = FakeMenu
    sys.modules["pokemon.utils.enhanced_evmenu"] = fake_evmod

    orig_mgr = sys.modules.get("menus.moveset_manager")
    fake_mgr = types.ModuleType("menus.moveset_manager")
    sys.modules["menus.moveset_manager"] = fake_mgr

    path = os.path.join(ROOT, "commands", "cmd_movesets.py")
    spec = importlib.util.spec_from_file_location("commands.cmd_movesets", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

    if orig_evennia is not None:
        sys.modules["evennia"] = orig_evennia
    else:
        sys.modules.pop("evennia", None)
    if orig_evmod is not None:
        sys.modules["pokemon.utils.enhanced_evmenu"] = orig_evmod
    else:
        sys.modules.pop("pokemon.utils.enhanced_evmenu", None)
    if orig_mgr is not None:
        sys.modules["menus.moveset_manager"] = orig_mgr
    else:
        sys.modules.pop("menus.moveset_manager", None)

    class DummyLoc:
        def __init__(self):
            self.db = types.SimpleNamespace(is_pokemon_center=False)

    class DummyCaller:
        def __init__(self):
            self.msgs = []
            self.location = DummyLoc()
        def msg(self, text):
            self.msgs.append(text)

    caller = DummyCaller()
    cmd = mod.CmdMovesets()
    cmd.caller = caller
    cmd.func()

    assert not FakeMenu.called
    assert caller.msgs and "Pokémon Center" in caller.msgs[-1]

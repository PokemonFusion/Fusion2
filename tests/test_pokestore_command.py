import os
import sys
import types
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module():
    path = os.path.join(ROOT, "commands", "cmd_pokestore.py")
    spec = importlib.util.spec_from_file_location("commands.cmd_pokestore", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_pokestore_invalid_location():
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

    orig_menu = sys.modules.get("menus.pokestore")
    fake_menu = types.ModuleType("menus.pokestore")
    sys.modules["menus.pokestore"] = fake_menu

    mod = load_cmd_module()

    if orig_evennia is not None:
        sys.modules["evennia"] = orig_evennia
    else:
        sys.modules.pop("evennia", None)
    if orig_evmod is not None:
        sys.modules["pokemon.utils.enhanced_evmenu"] = orig_evmod
    else:
        sys.modules.pop("pokemon.utils.enhanced_evmenu", None)
    if orig_menu is not None:
        sys.modules["menus.pokestore"] = orig_menu
    else:
        sys.modules.pop("menus.pokestore", None)

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
    cmd = mod.CmdPokestore()
    cmd.caller = caller
    cmd.func()

    assert not FakeMenu.called
    assert caller.msgs and "Pokémon Center" in caller.msgs[-1]


def test_pokestore_opens_menu():
    orig_evennia = sys.modules.get("evennia")
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    sys.modules["evennia"] = fake_evennia

    orig_evmod = sys.modules.get("pokemon.utils.enhanced_evmenu")
    fake_evmod = types.ModuleType("pokemon.utils.enhanced_evmenu")
    class FakeMenu:
        called = False
        kwargs = None
        def __init__(self, caller, mod, startnode="node_start", kwargs=None, cmd_on_exit=None):
            FakeMenu.called = True
            FakeMenu.kwargs = kwargs
    fake_evmod.EnhancedEvMenu = FakeMenu
    sys.modules["pokemon.utils.enhanced_evmenu"] = fake_evmod

    orig_menu = sys.modules.get("menus.pokestore")
    fake_menu = types.ModuleType("menus.pokestore")
    sys.modules["menus.pokestore"] = fake_menu

    mod = load_cmd_module()

    if orig_evennia is not None:
        sys.modules["evennia"] = orig_evennia
    else:
        sys.modules.pop("evennia", None)
    if orig_evmod is not None:
        sys.modules["pokemon.utils.enhanced_evmenu"] = orig_evmod
    else:
        sys.modules.pop("pokemon.utils.enhanced_evmenu", None)
    if orig_menu is not None:
        sys.modules["menus.pokestore"] = orig_menu
    else:
        sys.modules.pop("menus.pokestore", None)

    class DummyLoc:
        def __init__(self):
            self.db = types.SimpleNamespace(is_pokemon_center=True)

    class DummyCaller:
        def __init__(self):
            self.msgs = []
            self.location = DummyLoc()
        def msg(self, text):
            self.msgs.append(text)

    caller = DummyCaller()
    cmd = mod.CmdPokestore()
    cmd.caller = caller
    cmd.func()

    assert FakeMenu.called


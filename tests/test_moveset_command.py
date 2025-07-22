import os
import sys
import types
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def test_choose_moveset_command():
    # Patch required modules
    orig_evennia = sys.modules.get("evennia")
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    sys.modules["evennia"] = fake_evennia

    orig_models = sys.modules.get("pokemon.models")
    fake_models = types.ModuleType("pokemon.models")
    fake_models.InventoryEntry = type("InventoryEntry", (), {})
    sys.modules["pokemon.models"] = fake_models

    orig_inv = sys.modules.get("utils.inventory")
    fake_inv = types.ModuleType("utils.inventory")
    fake_inv.add_item = lambda *a, **k: None
    fake_inv.remove_item = lambda *a, **k: True
    sys.modules["utils.inventory"] = fake_inv

    orig_dex = sys.modules.get("pokemon.dex")
    fake_dex = types.ModuleType("pokemon.dex")
    fake_dex.ITEMDEX = {}
    fake_dex.POKEDEX = {}
    sys.modules["pokemon.dex"] = fake_dex

    # Load command module with stubs
    path = os.path.join(ROOT, "commands", "command.py")
    spec = importlib.util.spec_from_file_location("commands.command", path)
    cmd_mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = cmd_mod
    spec.loader.exec_module(cmd_mod)

    # Restore modules
    if orig_evennia is not None:
        sys.modules["evennia"] = orig_evennia
    else:
        sys.modules.pop("evennia", None)
    if orig_models is not None:
        sys.modules["pokemon.models"] = orig_models
    else:
        sys.modules.pop("pokemon.models", None)
    if orig_inv is not None:
        sys.modules["utils.inventory"] = orig_inv
    else:
        sys.modules.pop("utils.inventory", None)
    if orig_dex is not None:
        sys.modules["pokemon.dex"] = orig_dex
    else:
        sys.modules.pop("pokemon.dex", None)

    class DummyPokemon:
        def __init__(self):
            self.movesets = [["tackle"], [], [], []]
            self.called = None
            self.name = "Dummy"

        @property
        def computed_level(self):
            return 1

        def swap_moveset(self, idx):
            self.called = idx

    class DummyCaller:
        def __init__(self, poke):
            self.poke = poke
            self.msgs = []

        def get_active_pokemon_by_slot(self, slot):
            return self.poke if slot == 1 else None

        def msg(self, text):
            self.msgs.append(text)

    poke = DummyPokemon()
    caller = DummyCaller(poke)
    cmd = cmd_mod.CmdChooseMoveset()
    cmd.caller = caller
    cmd.args = "1=1"
    cmd.parse()
    cmd.func()

    assert poke.called == 0
    assert caller.msgs and "moveset 1" in caller.msgs[-1]

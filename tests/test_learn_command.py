import os
import sys
import types
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module():
    path = os.path.join(ROOT, "commands", "cmd_learn_evolve.py")
    spec = importlib.util.spec_from_file_location("commands.cmd_learn_evolve", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def setup_modules():
    orig_evennia = sys.modules.get("evennia")
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    sys.modules["evennia"] = fake_evennia

    orig_menu = sys.modules.get("menus.learn_new_moves")
    fake_menu = types.ModuleType("menus.learn_new_moves")
    fake_menu.node_start = object
    sys.modules["menus.learn_new_moves"] = fake_menu

    orig_evmod = sys.modules.get("pokemon.utils.enhanced_evmenu")
    fake_evmod = types.ModuleType("pokemon.utils.enhanced_evmenu")

    class FakeMenu:
        called = False
        start_kwargs = None

        def __init__(self, caller, mod, startnode="node_start", start_kwargs=None, cmd_on_exit=None):
            FakeMenu.called = True
            FakeMenu.start_kwargs = start_kwargs

    fake_evmod.EnhancedEvMenu = FakeMenu
    sys.modules["pokemon.utils.enhanced_evmenu"] = fake_evmod

    orig_pokemon = sys.modules.get("pokemon")
    orig_gen = sys.modules.get("pokemon.generation")
    orig_models_pkg = sys.modules.get("pokemon.models")
    orig_models_moves = sys.modules.get("pokemon.models.moves")
    orig_models_trainer = sys.modules.get("pokemon.models.trainer")
    orig_stats = sys.modules.get("pokemon.stats")
    orig_dex = sys.modules.get("pokemon.dex")
    orig_breeding = sys.modules.get("pokemon.breeding")
    orig_mw = sys.modules.get("pokemon.middleware")
    orig_utils = sys.modules.get("pokemon.utils")
    orig_learn = sys.modules.get("pokemon.utils.move_learning")

    pokemon_pkg = types.ModuleType("pokemon")
    gen_mod = types.ModuleType("pokemon.generation")
    gen_mod.generate_pokemon = lambda *a, **k: None
    gen_mod.get_valid_moves = lambda species, lvl: []
    models_pkg = types.ModuleType("pokemon.models")
    trainer_mod = types.ModuleType("pokemon.models.trainer")
    trainer_mod.InventoryEntry = type("InventoryEntry", (), {})
    class FakeMove:
        def __init__(self, name):
            self.name = name
    class Manager:
        def get_or_create(self_inner, name):
            return FakeMove(name), True
    moves_mod = types.ModuleType("pokemon.models.moves")
    moves_mod.Move = type("Move", (), {"objects": Manager()})
    stats_mod = types.ModuleType("pokemon.stats")
    stats_mod.calculate_stats = lambda *a, **k: {}
    dex_mod = types.ModuleType("pokemon.dex")
    dex_mod.ITEMDEX = {}
    breeding_mod = types.ModuleType("pokemon.breeding")
    mw_mod = types.ModuleType("pokemon.middleware")
    mw_mod.get_moveset_by_name = lambda name: (None, {"level-up": []})

    pokemon_pkg.generation = gen_mod
    pokemon_pkg.models = models_pkg
    pokemon_pkg.stats = stats_mod
    pokemon_pkg.dex = dex_mod
    pokemon_pkg.breeding = breeding_mod
    pokemon_pkg.middleware = mw_mod

    sys.modules["pokemon"] = pokemon_pkg
    sys.modules["pokemon.generation"] = gen_mod
    sys.modules["pokemon.models"] = models_pkg
    sys.modules["pokemon.models.moves"] = moves_mod
    sys.modules["pokemon.models.trainer"] = trainer_mod
    sys.modules["pokemon.stats"] = stats_mod
    sys.modules["pokemon.dex"] = dex_mod
    sys.modules["pokemon.breeding"] = breeding_mod
    sys.modules["pokemon.middleware"] = mw_mod

    utils_mod = types.ModuleType("pokemon.utils")
    helpers_mod = types.ModuleType("pokemon.utils.pokemon_helpers")
    helpers_mod.get_max_hp = lambda *a, **k: 35
    helpers_mod.get_stats = lambda *a, **k: {}
    utils_mod.pokemon_helpers = helpers_mod
    sys.modules["pokemon.utils"] = utils_mod
    sys.modules["pokemon.utils.pokemon_helpers"] = helpers_mod

    learn_mod = types.ModuleType("pokemon.utils.move_learning")
    learn_mod.learn_move = lambda *a, **k: None
    learn_mod.get_learnable_levelup_moves = lambda poke: ([], {})
    sys.modules["pokemon.utils.move_learning"] = learn_mod

    orig_inv = sys.modules.get("utils.inventory")
    fake_inv = types.ModuleType("utils.inventory")
    fake_inv.add_item = lambda *a, **k: None
    fake_inv.remove_item = lambda *a, **k: True
    sys.modules["utils.inventory"] = fake_inv

    return (
        orig_evennia,
        orig_menu,
        orig_evmod,
        orig_pokemon,
        orig_gen,
        orig_models_pkg,
        orig_models_moves,
        orig_models_trainer,
        orig_stats,
        orig_dex,
        orig_breeding,
        orig_mw,
        orig_inv,
        orig_utils,
        orig_learn,
        FakeMenu,
    )


def restore_modules(
    orig_evennia,
    orig_menu,
    orig_evmod,
    orig_pokemon,
    orig_gen,
    orig_models_pkg,
    orig_models_moves,
    orig_models_trainer,
    orig_stats,
    orig_dex,
    orig_breeding,
    orig_mw,
    orig_inv,
    orig_utils,
    orig_learn,
):
    if orig_evennia is not None:
        sys.modules["evennia"] = orig_evennia
    else:
        sys.modules.pop("evennia", None)
    if orig_menu is not None:
        sys.modules["menus.learn_new_moves"] = orig_menu
    else:
        sys.modules.pop("menus.learn_new_moves", None)
    if orig_evmod is not None:
        sys.modules["pokemon.utils.enhanced_evmenu"] = orig_evmod
    else:
        sys.modules.pop("pokemon.utils.enhanced_evmenu", None)

    if orig_pokemon is not None:
        sys.modules["pokemon"] = orig_pokemon
    else:
        sys.modules.pop("pokemon", None)
    if orig_gen is not None:
        sys.modules["pokemon.generation"] = orig_gen
    else:
        sys.modules.pop("pokemon.generation", None)
    if orig_models_pkg is not None:
        sys.modules["pokemon.models"] = orig_models_pkg
    else:
        sys.modules.pop("pokemon.models", None)
    if orig_models_moves is not None:
        sys.modules["pokemon.models.moves"] = orig_models_moves
    else:
        sys.modules.pop("pokemon.models.moves", None)
    if orig_models_trainer is not None:
        sys.modules["pokemon.models.trainer"] = orig_models_trainer
    else:
        sys.modules.pop("pokemon.models.trainer", None)
    if orig_stats is not None:
        sys.modules["pokemon.stats"] = orig_stats
    else:
        sys.modules.pop("pokemon.stats", None)
    if orig_dex is not None:
        sys.modules["pokemon.dex"] = orig_dex
    else:
        sys.modules.pop("pokemon.dex", None)
    if orig_breeding is not None:
        sys.modules["pokemon.breeding"] = orig_breeding
    else:
        sys.modules.pop("pokemon.breeding", None)
    if orig_mw is not None:
        sys.modules["pokemon.middleware"] = orig_mw
    else:
        sys.modules.pop("pokemon.middleware", None)
    if orig_inv is not None:
        sys.modules["utils.inventory"] = orig_inv
    else:
        sys.modules.pop("utils.inventory", None)
    if orig_utils is not None:
        sys.modules["pokemon.utils"] = orig_utils
    else:
        sys.modules.pop("pokemon.utils", None)
    if orig_utils is not None and hasattr(orig_utils, "pokemon_helpers"):
        sys.modules["pokemon.utils.pokemon_helpers"] = orig_utils.pokemon_helpers
    else:
        sys.modules.pop("pokemon.utils.pokemon_helpers", None)
    if orig_learn is not None:
        sys.modules["pokemon.utils.move_learning"] = orig_learn
    else:
        sys.modules.pop("pokemon.utils.move_learning", None)


class DummyMoves:
    def __init__(self):
        self.data = []

    def all(self):
        return [types.SimpleNamespace(name=m) for m in self.data]


class DummyPokemon:
    def __init__(self):
        self.name = "Pika"
        self.learned_moves = DummyMoves()


class DummyCaller:
    def __init__(self, poke):
        self.poke = poke
        self.msgs = []

    def get_active_pokemon_by_slot(self, slot):
        return self.poke if slot == 1 else None

    def msg(self, text):
        self.msgs.append(text)


def test_learn_command_opens_menu():
    origs = setup_modules()
    fake_menu = origs[-1]
    cmd_mod = load_cmd_module()

    poke = DummyPokemon()
    caller = DummyCaller(poke)

    learn_mod = sys.modules["pokemon.utils.move_learning"]
    learn_mod.get_learnable_levelup_moves = lambda p: (["tackle"], {})

    cmd = cmd_mod.CmdLearn()
    cmd.caller = caller
    cmd.args = "1"
    cmd.parse()
    cmd.func()

    restore_modules(*origs[:-1])

    assert fake_menu.called
    assert fake_menu.start_kwargs["pokemon"] is poke


def test_learn_lists_pending_when_no_args():
    origs = setup_modules()
    fake_menu = origs[-1]
    cmd_mod = load_cmd_module()

    poke = DummyPokemon()
    caller = DummyCaller(poke)

    learn_mod = sys.modules["pokemon.utils.move_learning"]
    learn_mod.get_learnable_levelup_moves = lambda p: (["tackle"], {})

    cmd = cmd_mod.CmdLearn()
    cmd.caller = caller
    cmd.args = ""
    cmd.parse()
    cmd.func()

    restore_modules(*origs[:-1])

    assert not fake_menu.called
    assert any("Slot 1" in m for m in caller.msgs)


def test_learn_slot_with_no_moves():
    origs = setup_modules()
    fake_menu = origs[-1]
    cmd_mod = load_cmd_module()

    poke = DummyPokemon()
    caller = DummyCaller(poke)

    learn_mod = sys.modules["pokemon.utils.move_learning"]
    learn_mod.get_learnable_levelup_moves = lambda p: ([], {})

    cmd = cmd_mod.CmdLearn()
    cmd.caller = caller
    cmd.args = "1"
    cmd.parse()
    cmd.func()

    restore_modules(*origs[:-1])

    assert not fake_menu.called
    assert any("no moves" in m.lower() for m in caller.msgs)

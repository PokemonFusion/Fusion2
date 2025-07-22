import types
import sys
import os
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def test_learn_all_prompts_sequentially():
    orig_evmod = sys.modules.get("pokemon.utils.enhanced_evmenu")
    fake_evmod = types.ModuleType("pokemon.utils.enhanced_evmenu")
    fake_evmod.EnhancedEvMenu = object
    sys.modules["pokemon.utils.enhanced_evmenu"] = fake_evmod

    orig_gen = sys.modules.get("pokemon.generation")
    gen_mod = types.ModuleType("pokemon.generation")
    gen_mod.get_valid_moves = lambda *a, **k: []
    sys.modules["pokemon.generation"] = gen_mod

    orig_mw = sys.modules.get("pokemon.middleware")
    mw_mod = types.ModuleType("pokemon.middleware")
    mw_mod.get_moveset_by_name = lambda *a, **k: (None, {"level-up": []})
    sys.modules["pokemon.middleware"] = mw_mod

    orig_learn = sys.modules.get("pokemon.utils.move_learning")
    learn_mod = types.ModuleType("pokemon.utils.move_learning")
    calls = []

    def learn_move(pokemon, move_name, caller=None, prompt=False, on_exit=None):
        calls.append((pokemon, move_name, on_exit))
        if on_exit:
            on_exit(caller, None)

    learn_mod.learn_move = learn_move
    sys.modules["pokemon.utils.move_learning"] = learn_mod

    import importlib
    menu = importlib.import_module("menus.learn_new_moves")

    class DummyMoves:
        def __init__(self, moves):
            self.data = moves
        def all(self):
            return [types.SimpleNamespace(name=m) for m in self.data]

    class DummyPokemon:
        def __init__(self):
            self.name = "Pika"
            self.species = "pika"
            self.level = 5
            self.learned_moves = DummyMoves([])

        @property
        def computed_level(self):
            return self.level

    class DummyCaller:
        def __init__(self):
            self.msgs = []
        def msg(self, text):
            self.msgs.append(text)

    poke = DummyPokemon()
    caller = DummyCaller()

    menu.node_start(caller, raw_input="all", pokemon=poke, moves=["tackle", "growl"])

    if orig_learn is not None:
        sys.modules["pokemon.utils.move_learning"] = orig_learn
    else:
        sys.modules.pop("pokemon.utils.move_learning", None)
    if orig_evmod is not None:
        sys.modules["pokemon.utils.enhanced_evmenu"] = orig_evmod
    else:
        sys.modules.pop("pokemon.utils.enhanced_evmenu", None)
    if orig_gen is not None:
        sys.modules["pokemon.generation"] = orig_gen
    else:
        sys.modules.pop("pokemon.generation", None)
    if orig_mw is not None:
        sys.modules["pokemon.middleware"] = orig_mw
    else:
        sys.modules.pop("pokemon.middleware", None)
    sys.modules.pop("menus.learn_new_moves", None)
    sys.modules.pop("menus.learn_new_moves", None)

    assert len(calls) == 2
    assert calls[0][1] == "tackle"
    assert calls[1][1] == "growl"
    assert caller.msgs and "all available moves" in caller.msgs[-1]


def test_order_moves_by_level():
    orig_evmod = sys.modules.get("pokemon.utils.enhanced_evmenu")
    fake_evmod = types.ModuleType("pokemon.utils.enhanced_evmenu")
    fake_evmod.EnhancedEvMenu = object
    sys.modules["pokemon.utils.enhanced_evmenu"] = fake_evmod

    orig_learn = sys.modules.get("pokemon.utils.move_learning")
    learn_mod = types.ModuleType("pokemon.utils.move_learning")
    learn_mod.learn_move = lambda *a, **k: None
    sys.modules["pokemon.utils.move_learning"] = learn_mod

    orig_gen = sys.modules.get("pokemon.generation")
    gen_mod = types.ModuleType("pokemon.generation")
    gen_mod.get_valid_moves = lambda *a, **k: []
    sys.modules["pokemon.generation"] = gen_mod

    orig_mw = sys.modules.get("pokemon.middleware")
    mw_mod = types.ModuleType("pokemon.middleware")
    mw_mod.get_moveset_by_name = lambda name: (
        name,
        {"level-up": [(10, "ember"), (5, "scratch"), (7, "tailwhip")]},
    )
    sys.modules["pokemon.middleware"] = mw_mod

    import importlib
    menu = importlib.import_module("menus.learn_new_moves")

    class DummyMoves:
        def __init__(self, moves):
            self.data = moves

        def all(self):
            return [types.SimpleNamespace(name=m) for m in self.data]

    class DummyPokemon:
        def __init__(self):
            self.name = "Charm"
            self.species = "charmander"
            self.level = 10
            self.learned_moves = DummyMoves([])

        @property
        def computed_level(self):
            return self.level

    caller = types.SimpleNamespace(msgs=[], msg=lambda t: caller.msgs.append(t))

    text, _ = menu.node_start(caller, pokemon=DummyPokemon())
    lines = [ln.strip() for ln in text.splitlines()]

    if orig_evmod is not None:
        sys.modules["pokemon.utils.enhanced_evmenu"] = orig_evmod
    else:
        sys.modules.pop("pokemon.utils.enhanced_evmenu", None)
    if orig_learn is not None:
        sys.modules["pokemon.utils.move_learning"] = orig_learn
    else:
        sys.modules.pop("pokemon.utils.move_learning", None)
    if orig_gen is not None:
        sys.modules["pokemon.generation"] = orig_gen
    else:
        sys.modules.pop("pokemon.generation", None)
    if orig_mw is not None:
        sys.modules["pokemon.middleware"] = orig_mw
    else:
        sys.modules.pop("pokemon.middleware", None)

    assert lines[1].startswith("Lv5") and "Scratch" in lines[1]
    assert lines[2].startswith("Lv7") and "Tailwhip" in lines[2]
    assert lines[3].startswith("Lv10") and "Ember" in lines[3]

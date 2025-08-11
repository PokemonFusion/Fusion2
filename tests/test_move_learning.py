import importlib.util
import sys
import types
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def test_on_exit_called_when_auto_learn():
    pokemon_pkg = types.ModuleType("pokemon")
    pokemon_pkg.__path__ = []
    utils_pkg = types.ModuleType("pokemon.utils")
    enhanced_mod = types.ModuleType("helpers.enhanced_evmenu")
    enhanced_mod.EnhancedEvMenu = object
    utils_pkg.enhanced_evmenu = enhanced_mod
    models_mod = types.ModuleType("pokemon.models.moves")
    services_pkg = types.ModuleType("pokemon.services")
    move_service_mod = types.ModuleType("pokemon.services.move_management")
    move_service_mod.apply_active_moveset = lambda *a, **k: None
    services_pkg.move_management = move_service_mod

    class FakeMove:
        def __init__(self, name):
            self.name = name

    class Manager:
        def get_or_create(self, name):
            return FakeMove(name), True

    models_mod.Move = type("Move", (), {"objects": Manager()})

    orig_pokemon = sys.modules.get("pokemon")
    orig_utils = sys.modules.get("pokemon.utils")
    orig_enh = sys.modules.get("helpers.enhanced_evmenu")
    orig_models = sys.modules.get("pokemon.models")

    sys.modules["pokemon"] = pokemon_pkg
    sys.modules["pokemon.utils"] = utils_pkg
    sys.modules["helpers.enhanced_evmenu"] = enhanced_mod
    sys.modules["pokemon.models.moves"] = models_mod
    sys.modules["pokemon.services"] = services_pkg
    sys.modules["pokemon.services.move_management"] = move_service_mod

    path = os.path.join(ROOT, "pokemon", "utils", "move_learning.py")
    spec = importlib.util.spec_from_file_location(
        "pokemon.utils.move_learning", path
    )
    ml = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = ml
    spec.loader.exec_module(ml)

    class DummyMoves(list):
        def filter(self, **kw):
            name = kw.get("name__iexact", "").lower()
            return DummyMoves([m for m in self if m.name.lower() == name])

        def exists(self):
            return bool(self)

        def add(self, obj):
            self.append(obj)

    class DummySlots(list):
        def order_by(self, field):
            return self
        def create(self, move, slot):
            obj = types.SimpleNamespace(move=move, slot=slot)
            self.append(obj)
            return obj

    class DummyMoveset:
        def __init__(self, index):
            self.index = index
            self.slots = DummySlots()

    class MovesetManager(list):
        def all(self):
            return self
        def order_by(self, field):
            return sorted(self, key=lambda m: m.index)
        def exists(self):
            return bool(self)
        def create(self, index):
            ms = DummyMoveset(index)
            self.append(ms)
            return ms
        def get_or_create(self, index):
            for ms in self:
                if ms.index == index:
                    return ms, False
            return self.create(index), True

    class DummyPokemon:
        def __init__(self):
            self.name = "Pika"
            self.movesets = MovesetManager()
            ms = self.movesets.create(0)
            self.active_moveset = ms
            self.learned_moves = DummyMoves()
            self.species = "pika"
            self.level = 5

        def save(self):
            pass

        def apply_active_moveset(self):
            pass

    poke = DummyPokemon()
    called = []
    ml.learn_move(
        poke, "tackle", caller=None, prompt=True, on_exit=lambda *a: called.append(True)
    )

    if orig_pokemon is not None:
        sys.modules["pokemon"] = orig_pokemon
    else:
        sys.modules.pop("pokemon", None)
    if orig_utils is not None:
        sys.modules["pokemon.utils"] = orig_utils
    else:
        sys.modules.pop("pokemon.utils", None)
    if orig_enh is not None:
        sys.modules["helpers.enhanced_evmenu"] = orig_enh
    else:
        sys.modules.pop("helpers.enhanced_evmenu", None)
    if orig_models is not None:
        sys.modules["pokemon.models"] = orig_models
    else:
        sys.modules.pop("pokemon.models", None)
    sys.modules.pop("pokemon.services", None)
    sys.modules.pop("pokemon.services.move_management", None)
    sys.modules.pop("pokemon.utils.move_learning", None)

    assert called

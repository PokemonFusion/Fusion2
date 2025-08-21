import importlib.util
import os
import sys
import types

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Stub utils
utils_stub = types.ModuleType("pokemon.battle.utils")


def apply_boost(pokemon, boosts):
    pass


utils_stub.apply_boost = apply_boost
pkg_battle = types.ModuleType("pokemon.battle")
pkg_battle.__path__ = []
pkg_battle.utils = utils_stub
sys.modules["pokemon.battle"] = pkg_battle
sys.modules["pokemon.battle.utils"] = utils_stub

# Load entities
entities_path = os.path.join(ROOT, "pokemon", "dex", "entities.py")
ent_spec = importlib.util.spec_from_file_location("pokemon.dex.entities", entities_path)
ent_mod = importlib.util.module_from_spec(ent_spec)
sys.modules[ent_spec.name] = ent_mod
ent_spec.loader.exec_module(ent_mod)

# Build minimal pokemon.dex
pokemon_dex = types.ModuleType("pokemon.dex")
pokemon_dex.__path__ = []
pokemon_dex.entities = ent_mod
pokemon_dex.MOVEDEX = {
    "tackle": types.SimpleNamespace(
        name="Tackle", type="Normal", category="Physical", power=40, accuracy=100, raw={"priority": 0}
    )
}
pokemon_dex.POKEDEX = {"Bulbasaur": types.SimpleNamespace(num=1, name="Bulbasaur", types=["Grass", "Poison"])}
sys.modules["pokemon.dex"] = pokemon_dex

# Load battledata
bd_path = os.path.join(ROOT, "pokemon", "battle", "battledata.py")
bd_spec = importlib.util.spec_from_file_location("pokemon.battle.battledata", bd_path)
battledata = importlib.util.module_from_spec(bd_spec)
sys.modules[bd_spec.name] = battledata
bd_spec.loader.exec_module(battledata)
Pokemon = battledata.Pokemon

# Load moves_funcs
moves_path = os.path.join(ROOT, "pokemon", "dex", "functions", "moves_funcs.py")
mv_spec = importlib.util.spec_from_file_location("pokemon.dex.functions.moves_funcs", moves_path)
mv_mod = importlib.util.module_from_spec(mv_spec)
sys.modules[mv_spec.name] = mv_mod
mv_spec.loader.exec_module(mv_mod)
Afteryou = mv_mod.Afteryou


@pytest.fixture(autouse=True)
def _cleanup_modules():
    yield
    for mod in ("pokemon.dex", "pokemon.battle", "pokemon.battle.utils"):
        sys.modules.pop(mod, None)


class DummyQueue:
    def __init__(self):
        self.prioritized = None

    def will_move(self, target):
        return object()

    def prioritize_action(self, action):
        self.prioritized = action


class DummyBattle:
    def __init__(self, active_per_side, queue=None):
        part = types.SimpleNamespace(active=[object()] * active_per_side)
        self.participants = [part, part]
        self.queue = queue


def test_afteryou_fails_in_singles():
    user = Pokemon("User")
    target = Pokemon("Target")
    battle = DummyBattle(active_per_side=1, queue=DummyQueue())
    result = Afteryou().onHit(user, target, battle)
    assert result is False
    assert battle.queue.prioritized is None


def test_afteryou_prioritizes_target_in_doubles():
    user = Pokemon("User")
    target = Pokemon("Target")
    q = DummyQueue()
    battle = DummyBattle(active_per_side=2, queue=q)
    result = Afteryou().onHit(user, target, battle)
    assert result is True
    assert q.prioritized is not None

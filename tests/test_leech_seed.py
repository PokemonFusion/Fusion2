import importlib.util
import os
import types
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Provide minimal battle utils for imports
pkg_battle = types.ModuleType("pokemon.battle")
utils_stub = types.ModuleType("pokemon.battle.utils")
utils_stub.apply_boost = lambda *a, **k: None
pkg_battle.utils = utils_stub
pkg_battle.__path__ = []
sys.modules["pokemon.battle"] = pkg_battle
sys.modules["pokemon.battle.utils"] = utils_stub

# Load simple Pokemon container
bd_spec = importlib.util.spec_from_file_location(
    "pokemon.battle.battledata",
    os.path.join(ROOT, "pokemon", "battle", "battledata.py"),
)
bd_mod = importlib.util.module_from_spec(bd_spec)
sys.modules[bd_spec.name] = bd_mod
bd_spec.loader.exec_module(bd_mod)
Pokemon = bd_mod.Pokemon

# Load Leechseed implementation
mv_spec = importlib.util.spec_from_file_location(
    "pokemon.dex.functions.moves_funcs",
    os.path.join(ROOT, "pokemon", "dex", "functions", "moves_funcs.py"),
)
mv_mod = importlib.util.module_from_spec(mv_spec)
sys.modules[mv_spec.name] = mv_mod
mv_spec.loader.exec_module(mv_mod)
Leechseed = mv_mod.Leechseed


def test_leech_seed_drains_and_heals():
    seeder = Pokemon("Seeder", 1, 50, 100)
    target = Pokemon("Target", 1, 100, 100)
    target.volatiles = {}
    Leechseed().onStart(seeder, target)
    Leechseed().onResidual(target)
    assert target.hp == 88
    assert seeder.hp == 62


def test_leech_seed_removed_when_source_faints():
    seeder = Pokemon("Seeder", 1, 50, 100)
    target = Pokemon("Target", 1, 100, 100)
    target.volatiles = {}
    Leechseed().onStart(seeder, target)
    seeder.hp = 0
    Leechseed().onResidual(target)
    assert "leechseed" not in target.volatiles

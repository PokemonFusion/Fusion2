import importlib.util
import os
import sys
import types

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Prepare minimal pokemon.battle.utils stub for apply_boost
utils_stub = types.ModuleType("pokemon.battle.utils")


def apply_boost(pokemon, boosts):
	if not hasattr(pokemon, "boosts"):
		return
	for stat, amount in boosts.items():
		cur = pokemon.boosts.get(stat, 0)
		pokemon.boosts[stat] = max(-6, min(6, cur + amount))


utils_stub.apply_boost = apply_boost
pkg_battle = types.ModuleType("pokemon.battle")
pkg_battle.__path__ = []
pkg_battle.utils = utils_stub
sys.modules["pokemon.battle"] = pkg_battle
sys.modules["pokemon.battle.utils"] = utils_stub

# Load entities module for dataclasses
entities_path = os.path.join(ROOT, "pokemon", "dex", "entities.py")
ent_spec = importlib.util.spec_from_file_location("pokemon.dex.entities", entities_path)
ent_mod = importlib.util.module_from_spec(ent_spec)
sys.modules[ent_spec.name] = ent_mod
ent_spec.loader.exec_module(ent_mod)

# Build minimal pokemon.dex package using entities
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

# Load moves_funcs using stub engine
moves_path = os.path.join(ROOT, "pokemon", "dex", "functions", "moves_funcs.py")
mv_spec = importlib.util.spec_from_file_location("pokemon.dex.functions.moves_funcs", moves_path)
mv_mod = importlib.util.module_from_spec(mv_spec)
sys.modules[mv_spec.name] = mv_mod
mv_spec.loader.exec_module(mv_mod)
Acupressure = mv_mod.Acupressure


@pytest.fixture(autouse=True)
def _cleanup_modules():
	yield
	for mod in ("pokemon.dex", "pokemon.battle", "pokemon.battle.utils"):
		sys.modules.pop(mod, None)


class DummyMove:
	def __init__(self, onHit=None):
		self.onHit = onHit


def test_acupressure_boosts_one_stat():
	user = Pokemon("User")
	target = Pokemon("Target")
	move = DummyMove(Acupressure().onHit)
	move.onHit(user, target, None)
	assert sum(1 for v in target.boosts.values() if v == 2) == 1


def test_acupressure_fails_when_maxed():
	user = Pokemon("User")
	target = Pokemon("Target")
	target.boosts = {stat: 6 for stat in target.boosts}
	move = DummyMove(Acupressure().onHit)
	result = move.onHit(user, target, None)
	assert result is False
	assert all(v == 6 for v in target.boosts.values())

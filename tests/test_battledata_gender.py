import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

pokemon_pkg = sys.modules.get("pokemon")
if pokemon_pkg is None:
	pokemon_pkg = types.ModuleType("pokemon")
	sys.modules["pokemon"] = pokemon_pkg
pokemon_pkg.__path__ = [str(ROOT / "pokemon")]

battle_pkg = sys.modules.get("pokemon.battle")
if battle_pkg is None:
	battle_pkg = types.ModuleType("pokemon.battle")
	sys.modules["pokemon.battle"] = battle_pkg
battle_pkg.__path__ = [str(ROOT / "pokemon" / "battle")]

dex_stub = types.ModuleType("pokemon.dex")
dex_stub.POKEDEX = {}
sys.modules.setdefault("pokemon.dex", dex_stub)

spec = importlib.util.spec_from_file_location(
	"pokemon.battle.battledata", ROOT / "pokemon" / "battle" / "battledata.py"
)
bd_mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = bd_mod
spec.loader.exec_module(bd_mod)
Pokemon = bd_mod.Pokemon


def test_pokemon_to_dict_from_dict_gender():
	p = Pokemon("Eevee", gender="F")
	data = p.to_dict()
	assert data["gender"] == "F"
	restored = Pokemon.from_dict(data)
	assert restored.gender == "F"

import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

# Build minimal pokemon.dex package with base stats
entities_path = os.path.join(ROOT, "pokemon", "dex", "entities.py")
ent_spec = importlib.util.spec_from_file_location("pokemon.dex.entities", entities_path)
ent_mod = importlib.util.module_from_spec(ent_spec)
sys.modules[ent_spec.name] = ent_mod
ent_spec.loader.exec_module(ent_mod)
pokemon_dex = types.ModuleType("pokemon.dex")
pokemon_dex.__path__ = [os.path.join(ROOT, "pokemon", "dex")]
pokemon_dex.entities = ent_mod
pokemon_dex.POKEDEX = {
	"Bulbasaur": ent_mod.Pokemon(
		name="Bulbasaur",
		num=1,
		types=["Grass", "Poison"],
		gender_ratio=None,
		base_stats=ent_mod.Stats(
			hp=45,
			attack=49,
			defense=49,
			special_attack=65,
			special_defense=65,
			speed=45,
		),
		abilities={},
	)
}
pokemon_dex.MOVEDEX = {}
sys.modules["pokemon.dex"] = pokemon_dex
import pokemon.models.stats as stats_mod

stats_mod.POKEDEX = pokemon_dex.POKEDEX

from pokemon.models.stats import (
	add_evs,
	add_experience,
	calculate_stats,
	exp_for_level,
	get_trainer_xp,
	level_for_exp,
	set_trainer_xp,
)


def test_exp_level_conversion():
	for rate in ["fast", "medium_fast", "slow", "medium_slow", "fluctuating"]:
		for level in [1, 5, 10, 50]:
			exp = exp_for_level(level, rate)
			assert level_for_exp(exp, rate) == level
			# exp just below should yield level-1
			if level > 1:
				assert level_for_exp(exp - 1, rate) == level - 1


def test_add_experience_updates_level():
	mon = types.SimpleNamespace(experience=0, level=1, growth_rate="medium_fast")
	add_experience(mon, exp_for_level(10) - 1)
	assert mon.level == 9
	add_experience(mon, 1)
	assert mon.level == 10


def test_set_trainer_xp_updates_legacy_and_named_attrs():
	player = types.SimpleNamespace(db=types.SimpleNamespace(txp=12))

	total = set_trainer_xp(player, 50)

	assert total == 50
	assert get_trainer_xp(player) == 50
	assert player.db.trainer_xp == 50
	assert player.db.txp == 50


def test_add_evs_limits():
	mon = types.SimpleNamespace(evs={})
	add_evs(mon, {"atk": 100, "def": 200, "spa": 300})
	assert mon.evs["attack"] == 100
	assert mon.evs["defense"] == 200
	assert mon.evs["special_attack"] == 210
	assert sum(mon.evs.values()) == 510


def test_add_evs_preserves_array_storage_and_stat_order():
	"""Battle rewards must leave PostgreSQL EV arrays as six numeric values."""
	mon = types.SimpleNamespace(evs=[0, 250, 0, 0, 0, 0])
	add_evs(mon, {"atk": 10, "spa": 4, "spe": 2})
	assert mon.evs == [0, 252, 0, 4, 0, 2]


def test_add_evs_array_obeys_total_limit():
	"""An array-backed Pokemon uses the same per-stat and total EV limits."""
	mon = types.SimpleNamespace(evs=[252, 250, 0, 0, 0, 0])
	add_evs(mon, {"atk": 10, "def": 20})
	assert mon.evs == [252, 252, 6, 0, 0, 0]


def test_add_evs_preserves_empty_array_default():
	"""An empty ArrayField default also becomes a legal six-value EV array."""
	mon = types.SimpleNamespace(evs=[])
	add_evs(mon, {"spe": 1})
	assert mon.evs == [0, 0, 0, 0, 0, 1]


def test_calculate_stats_with_ivs_evs_and_nature():
	ivs = {
		stat: 31
		for stat in [
			"hp",
			"attack",
			"defense",
			"special_attack",
			"special_defense",
			"speed",
		]
	}
	evs = {
		"attack": 100,
		"defense": 200,
		"special_attack": 210,
		"hp": 0,
		"special_defense": 0,
		"speed": 0,
	}
	stats = calculate_stats("Bulbasaur", 50, ivs, evs, "Adamant")
	assert stats["hp"] == 120
	assert stats["attack"] == 90
	assert stats["defense"] == 94
	assert stats["special_attack"] == 99
	assert stats["special_defense"] == 85
	assert stats["speed"] == 65

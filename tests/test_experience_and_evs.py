import os
import sys
import types
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Build minimal pokemon.dex package with base stats
entities_path = os.path.join(ROOT, "pokemon", "dex", "entities.py")
ent_spec = importlib.util.spec_from_file_location("pokemon.dex.entities", entities_path)
ent_mod = importlib.util.module_from_spec(ent_spec)
sys.modules[ent_spec.name] = ent_mod
ent_spec.loader.exec_module(ent_mod)
pokemon_dex = types.ModuleType("pokemon.dex")
pokemon_dex.__path__ = []
pokemon_dex.entities = ent_mod
pokemon_dex.POKEDEX = {
    "Bulbasaur": ent_mod.Pokemon(
        name="Bulbasaur",
        num=1,
        types=["Grass", "Poison"],
        gender_ratio=None,
        base_stats=ent_mod.Stats(hp=45, atk=49, def_=49, spa=65, spd=65, spe=45),
        abilities={},
    )
}
sys.modules["pokemon.dex"] = pokemon_dex
import pokemon.stats as stats_mod
stats_mod.POKEDEX = pokemon_dex.POKEDEX

from pokemon.stats import (
    exp_for_level,
    level_for_exp,
    add_experience,
    add_evs,
    calculate_stats,
)


def test_exp_level_conversion():
    for rate in ["fast", "medium_fast", "slow", "medium_slow"]:
        for level in [1, 5, 10, 50]:
            exp = exp_for_level(level, rate)
            assert level_for_exp(exp, rate) == level
            # exp just below should yield level-1
            if level > 1:
                assert level_for_exp(exp - 1, rate) == level - 1


def test_add_experience_updates_level():
    mon = types.SimpleNamespace(experience=0, level=1, data={"growth_rate": "medium_fast"})
    add_experience(mon, exp_for_level(10) - 1)
    assert mon.level == 9
    add_experience(mon, 1)
    assert mon.level == 10


def test_add_evs_limits():
    mon = types.SimpleNamespace(evs={})
    add_evs(mon, {"atk": 100, "def": 200, "spa": 300})
    assert mon.evs["atk"] == 100
    assert mon.evs["def"] == 200
    assert mon.evs["spa"] == 210
    assert sum(mon.evs.values()) == 510


def test_calculate_stats_with_ivs_evs_and_nature():
    ivs = {stat: 31 for stat in ["hp", "atk", "def", "spa", "spd", "spe"]}
    evs = {"atk": 100, "def": 200, "spa": 210, "hp": 0, "spd": 0, "spe": 0}
    stats = calculate_stats("Bulbasaur", 50, ivs, evs, "Adamant")
    assert stats["hp"] == 120
    assert stats["atk"] == 90
    assert stats["def"] == 94
    assert stats["spa"] == 99
    assert stats["spd"] == 85
    assert stats["spe"] == 65

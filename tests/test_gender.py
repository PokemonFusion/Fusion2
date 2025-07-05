import os
import sys
import types
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Minimal pokemon.dex stub
entities_path = os.path.join(ROOT, "pokemon", "dex", "entities.py")
ent_spec = importlib.util.spec_from_file_location("pokemon.dex.entities", entities_path)
ent_mod = importlib.util.module_from_spec(ent_spec)
sys.modules[ent_spec.name] = ent_mod
ent_spec.loader.exec_module(ent_mod)

pokemon_dex = types.ModuleType("pokemon.dex")
pokemon_dex.__path__ = []
pokemon_dex.entities = ent_mod
pokemon_dex.POKEDEX = {}
pokemon_dex.MOVEDEX = {}
sys.modules["pokemon.dex"] = pokemon_dex

# Load generation module
gen_path = os.path.join(ROOT, "pokemon", "generation.py")
gen_spec = importlib.util.spec_from_file_location("pokemon.generation", gen_path)
gen_mod = importlib.util.module_from_spec(gen_spec)
sys.modules[gen_spec.name] = gen_mod
gen_spec.loader.exec_module(gen_mod)
get_gender = gen_mod.get_gender


def test_get_gender_single():
    assert get_gender(single="M") == "M"
    assert get_gender(single="F") == "F"
    assert get_gender(single="N") == "N"


def test_get_gender_ratio_special_cases():
    assert get_gender({"M": 0, "F": 0}) == "N"
    assert get_gender({"M": 1, "F": 0}) == "M"
    assert get_gender({"M": 0, "F": 1}) == "F"

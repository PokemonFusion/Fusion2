import importlib.util
import os
import sys
import types

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

# Load entity definitions
entities_path = os.path.join(ROOT, "pokemon", "dex", "entities.py")
ent_spec = importlib.util.spec_from_file_location("pokemon.dex.entities", entities_path)
ent_mod = importlib.util.module_from_spec(ent_spec)
sys.modules[ent_spec.name] = ent_mod
ent_spec.loader.exec_module(ent_mod)

# Load generation module for PokemonInstance class
gen_path = os.path.join(ROOT, "pokemon", "data", "generation.py")
gen_spec = importlib.util.spec_from_file_location("pokemon.data.generation", gen_path)
gen_mod = importlib.util.module_from_spec(gen_spec)
sys.modules[gen_spec.name] = gen_mod
gen_spec.loader.exec_module(gen_mod)
PokemonInstance = gen_mod.PokemonInstance

# Build minimal pokedex
pokemon_dex = types.ModuleType("pokemon.dex")
pokemon_dex.__path__ = [os.path.join(ROOT, "pokemon", "dex")]
pokemon_dex.entities = ent_mod
pokemon_dex.POKEDEX = {
	"ditto": ent_mod.Pokemon(name="Ditto", num=132, egg_groups=["Ditto"], raw={}),
	"pikachu": ent_mod.Pokemon(
		name="Pikachu",
		num=25,
		egg_groups=["Field", "Fairy"],
		prevo="Pichu",
		raw={"prevo": "Pichu"},
	),
	"pichu": ent_mod.Pokemon(name="Pichu", num=172, egg_groups=["Undiscovered"], raw={}),
	"geodude": ent_mod.Pokemon(name="Geodude", num=74, egg_groups=["Mineral"], raw={}),
	"volbeat": ent_mod.Pokemon(
		name="Volbeat",
		num=313,
		egg_groups=["Bug", "Human-Like"],
		gender="M",
		raw={"mother": "illumise"},
	),
	"illumise": ent_mod.Pokemon(
		name="Illumise",
		num=314,
		egg_groups=["Bug", "Human-Like"],
		gender="F",
		raw={},
	),
}
sys.modules["pokemon.dex"] = pokemon_dex

# Load breeding module
breed_path = os.path.join(ROOT, "pokemon", "data", "breeding.py")
breed_spec = importlib.util.spec_from_file_location("pokemon.data.breeding", breed_path)
breed_mod = importlib.util.module_from_spec(breed_spec)
sys.modules[breed_spec.name] = breed_mod
breed_spec.loader.exec_module(breed_mod)
breed_mod.POKEDEX = pokemon_dex.POKEDEX


def make_instance(name, gender):
	return PokemonInstance(
		species=pokemon_dex.POKEDEX[name],
		level=5,
		ivs=ent_mod.Stats(),
		stats=ent_mod.Stats(),
		moves=[],
		ability="",
		gender=gender,
		nature="Hardy",
	)


def test_ditto_breeding_returns_base_form():
	mom = make_instance("pikachu", "F")
	dad = make_instance("ditto", "N")
	assert breed_mod.determine_egg_species(mom, dad) == "Pichu"


def test_incompatible_egg_groups_raise():
	mom = make_instance("pikachu", "F")
	dad = make_instance("geodude", "M")  # different groups, ordinary supported species
	with pytest.raises(ValueError):
		breed_mod.determine_egg_species(mom, dad)


def test_special_case_volbeat_requires_explicit_counterpart_rule():
	dad = make_instance("volbeat", "M")
	ditto = make_instance("ditto", "N")
	with pytest.raises(ValueError, match="Special offspring"):
		breed_mod.determine_egg_species(dad, ditto)


def test_two_ditto_and_invalid_gender_are_rejected():
	ditto = make_instance("ditto", "N")
	with pytest.raises(ValueError, match="Two Ditto"):
		breed_mod.determine_egg_species(ditto, ditto)
	with pytest.raises(ValueError, match="Invalid parent gender"):
		breed_mod.determine_egg_species(make_instance("pikachu", "X"), ditto)

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pokemon.data.starters import STARTER_NUMBERS, get_starter_names, resolve_starter_key


def test_starter_numbers_not_empty():
	assert len(STARTER_NUMBERS) > 0


def test_get_starter_names_contains_bulbasaur():
	names = get_starter_names()
	assert "Bulbasaur" in names


def test_normal_starters_remain_valid():
	names = get_starter_names()
	for species in ("Bulbasaur", "Charmander", "Squirtle", "Eevee"):
		assert species in names
		assert resolve_starter_key(species) is not None


def test_baby_evolution_included():
	names = get_starter_names()
	assert "Pichu" in names
	assert "Pikachu" in names


def test_iron_crown_not_valid_starter():
	names = get_starter_names()
	assert "Iron Crown" not in names
	assert resolve_starter_key("Iron Crown") is None


def test_ultra_beast_not_valid_starter():
	names = get_starter_names()
	assert "Nihilego" not in names
	assert resolve_starter_key("Nihilego") is None


def test_paradox_pokemon_not_valid_starters():
	names = get_starter_names()
	for species in ("Great Tusk", "Iron Boulder", "Iron Valiant"):
		assert species not in names
		assert resolve_starter_key(species) is None

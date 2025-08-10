import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from utils.pokemon_utils import (
    make_move_from_dex,
    make_pokemon_from_dict,
    make_pokemon_from_dex,
)
from pokemon.dex import POKEDEX


def test_create_pokemon_from_dict():
    data = {
        "species": "Bulbasaur",
        "level": 5,
        "stats": {"hp": 30},
        "moves": [{"name": "Tackle"}, {"name": "Growl"}],
    }

    poke = make_pokemon_from_dict(data)
    assert poke.name == "Bulbasaur"
    assert poke.level == 5
    assert poke.hp == 30 and poke.max_hp == 30
    assert [m.name for m in poke.moves] == ["Tackle", "Growl"]


def test_defaults_when_fields_missing():
    # Only species is provided; other attributes should fall back to defaults
    poke = make_pokemon_from_dict({"name": "MissingNo"})
    assert poke.name == "MissingNo"
    assert poke.level == 1
    assert poke.moves and poke.moves[0].name == "Tackle"


def test_create_move_from_dex():
    absorb = make_move_from_dex("Absorb")
    assert absorb.name == "Absorb"


def test_create_pokemon_from_dex():
    poke = make_pokemon_from_dex("Bulbasaur", level=5, moves=["Absorb"])
    assert poke.name == "Bulbasaur"
    assert poke.level == 5
    assert poke.max_hp == POKEDEX["Bulbasaur"].base_stats.hp
    assert [m.name for m in poke.moves] == ["Absorb"]

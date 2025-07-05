import os
import sys
import types
import importlib.util
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Minimal pokemon.dex stub
pokemon_dex = types.ModuleType("pokemon.dex")
pokemon_dex.__path__ = []
pokemon_dex.MOVEDEX = {
    "tackle": types.SimpleNamespace(
        name="Tackle",
        type="Normal",
        category="Physical",
        basePower=40,
        accuracy=100,
        raw={"priority": 0},
    ),
    "fling": types.SimpleNamespace(
        name="Fling",
        type="Dark",
        category="Physical",
        basePower=0,
        accuracy=100,
        raw={"priority": 0},
    ),
}
pokemon_dex.POKEDEX = {
    "bulbasaur": types.SimpleNamespace(num=1, name="Bulbasaur", types=["Grass"])
}
entities_path = os.path.join(ROOT, "pokemon", "dex", "entities.py")
ent_spec = importlib.util.spec_from_file_location("pokemon.dex.entities", entities_path)
ent_mod = importlib.util.module_from_spec(ent_spec)
sys.modules[ent_spec.name] = ent_mod
ent_spec.loader.exec_module(ent_mod)
pokemon_dex.entities = ent_mod
sys.modules["pokemon.dex"] = pokemon_dex

from pokemon.middleware import (
    get_move_by_name,
    format_move_details,
    get_pokemon_by_name,
    format_pokemon_details,
    get_move_description,
)


def test_get_move_by_name_tackle():
    key, move = get_move_by_name("tackle")
    assert key.lower() == "tackle"
    assert getattr(move, "name", "").lower() == "tackle"


def test_format_move_details():
    _, move = get_move_by_name("tackle")
    text = format_move_details("tackle", move)
    assert "Tackle" in text
    assert "Power" in text


def test_format_pokemon_details():
    name, details = get_pokemon_by_name("Bulbasaur")
    msg = format_pokemon_details(name, details)
    assert "Bulbasaur" in msg
    assert "#" in msg


def test_get_move_description_from_moves_text():
    _, move = get_move_by_name("Absorb")
    desc = get_move_description(move)
    assert "recovers" in desc.lower()


def test_get_move_description_fallback():
    fake_move = {"name": "FakeMove", "desc": "Some description."}
    assert get_move_description(fake_move) == "Some description."


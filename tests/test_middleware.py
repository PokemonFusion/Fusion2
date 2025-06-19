import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pokemon.middleware import (
    get_move_by_name,
    format_move_details,
    get_pokemon_by_name,
    format_pokemon_details,
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

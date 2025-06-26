import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pokemon.starters import STARTER_NUMBERS, get_starter_names


def test_starter_numbers_not_empty():
    assert len(STARTER_NUMBERS) > 0


def test_get_starter_names_contains_bulbasaur():
    names = get_starter_names()
    assert "Bulbasaur" in names

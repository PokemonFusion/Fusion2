"""Tests for type effectiveness messaging in damage calculations."""

import pytest

from pokemon import data as data_stub
from pokemon.battle import damage as dmg_module
from pokemon.battle.damage import damage_calc
from pokemon.data.text import DEFAULT_TEXT
from pokemon.dex.entities import Move, Pokemon, Stats


@pytest.fixture(autouse=True)
def _set_type_chart():
    chart = {
        "Fire": {"Grass": 1, "Fire": 2, "Water": 2},
        "Water": {"Rock": 1, "Ground": 1},
        "Electric": {"Ground": 3},
    }
    data_stub.TYPE_CHART = chart
    dmg_module.TYPE_CHART = chart


def make_pokemon(name, types):
    """Return a simple :class:`Pokemon` with balanced stats."""

    return Pokemon(
        name=name,
        num=1,
        types=types,
        base_stats=Stats(
            hp=100,
            attack=50,
            defense=50,
            special_attack=50,
            special_defense=50,
            speed=50,
        ),
    )


def make_move(name, type_):
    """Create a basic damaging move of the given type."""

    return Move(
        name=name,
        num=1,
        type=type_,
        category="Special",
        power=40,
        accuracy=100,
    )


def test_super_effective_message():
    attacker = make_pokemon("Charmander", ["Fire"])
    target = make_pokemon("Bulbasaur", ["Grass"])
    move = make_move("Flamethrower", "Fire")
    result = damage_calc(attacker, target, move)
    assert DEFAULT_TEXT["default"]["superEffective"] in result.text


def test_resisted_message():
    attacker = make_pokemon("Charmander", ["Fire"])
    target = make_pokemon("Flareon", ["Fire"])
    move = make_move("Flamethrower", "Fire")
    result = damage_calc(attacker, target, move)
    assert DEFAULT_TEXT["default"]["resisted"] in result.text


def test_double_super_effective_message():
    attacker = make_pokemon("Squirtle", ["Water"])
    target = make_pokemon("Geodude", ["Rock", "Ground"])
    move = make_move("Water Gun", "Water")
    result = damage_calc(attacker, target, move)
    assert (
        result.text.count(DEFAULT_TEXT["default"]["superEffective"]) == 2
    )


def test_double_resisted_message():
    attacker = make_pokemon("Charmander", ["Fire"])
    target = make_pokemon("Volcanion", ["Fire", "Water"])
    move = make_move("Flamethrower", "Fire")
    result = damage_calc(attacker, target, move)
    assert result.text.count(DEFAULT_TEXT["default"]["resisted"]) == 2


def test_immune_message_skips_damage():
    attacker = make_pokemon("Pikachu", ["Electric"])
    target = make_pokemon("Geodude", ["Ground"])
    move = make_move("Thunderbolt", "Electric")
    result = damage_calc(attacker, target, move)
    message = DEFAULT_TEXT["default"]["immune"].replace("[POKEMON]", target.name)
    assert result.text == [message]
    assert result.debug.get("damage") is None


"""Tests for minimum damage enforcement in damage calculations."""

from pokemon.dex.entities import Pokemon, Move, Stats
from pokemon.battle.damage import damage_calc
from pokemon import data as data_stub
from pokemon.battle import damage as dmg_module


def test_damage_minimum_one(monkeypatch):
    """Damage from damaging moves should never round down to zero."""
    chart = {"Fire": {"Fire": 2, "Water": 2}}
    data_stub.TYPE_CHART = chart
    dmg_module.TYPE_CHART = chart

    attacker = Pokemon(
        name="Attacker",
        num=1,
        types=["Electric"],
        base_stats=Stats(
            hp=100,
            attack=1,
            defense=1,
            special_attack=1,
            special_defense=1,
            speed=1,
        ),
    )
    target = Pokemon(
        name="Target",
        num=1,
        types=["Fire", "Water"],
        base_stats=Stats(
            hp=100,
            attack=1,
            defense=1,
            special_attack=1,
            special_defense=200,
            speed=1,
        ),
    )
    move = Move(
        name="Fire Move",
        num=1,
        type="Fire",
        category="Special",
        power=1,
        accuracy=100,
    )

    monkeypatch.setattr(dmg_module.random, "randint", lambda a, b: a)
    monkeypatch.setattr(dmg_module.random, "random", lambda: 0.9)

    result = damage_calc(attacker, target, move)
    assert result.debug["damage"][0] == 1

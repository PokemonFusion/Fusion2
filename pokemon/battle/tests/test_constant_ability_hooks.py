"""Literal false dex hooks must veto events just like callable false hooks."""

import copy
import random

import pytest

from .helpers import build_battle, load_modules


def damage(ability, name="Frost Breath"):
    """Observe actual critical-hit metadata with identical inputs and rolls."""
    from pokemon.battle.engine import _resolve_ability
    from pokemon.dex import MOVEDEX

    battle, user, target = build_battle(defender_ability=ability)
    move = copy.deepcopy(MOVEDEX[name.replace(" ", "").lower()])
    move.accuracy = True
    target.ability = _resolve_ability(ability)
    return load_modules()["damage_calc"](user, target, move, battle=battle, rng=random.Random(0))


@pytest.mark.parametrize("ability", ["Battle Armor", "Shell Armor"])
def test_literal_critical_hit_veto_prevents_guaranteed_criticals(ability):
    ordinary = damage("No Ability")
    guarded = damage(ability)
    assert ordinary.debug["critical"] == [True]
    assert guarded.debug["critical"] == [False]
    assert 0 < sum(guarded.debug["damage"]) < sum(ordinary.debug["damage"])


@pytest.mark.parametrize("ability", ["Battle Armor", "Shell Armor"])
def test_critical_protection_does_not_reduce_an_ordinary_noncritical_hit(ability):
    ordinary = damage("No Ability", "Tackle")
    guarded = damage(ability, "Tackle")
    assert ordinary.debug["critical"] == guarded.debug["critical"] == [False]
    assert guarded.debug["damage"] == ordinary.debug["damage"]


def test_false_ability_hook_and_absent_hook_remain_distinct():
    from pokemon.dex.entities import Ability

    ability = Ability.from_dict("Fixture", {"onCriticalHit": False, "onTryHit": True})
    assert ability.call("onCriticalHit", object()) is False
    assert ability.call("onTryHit", object()) is True
    assert ability.call("onMissingHook", object()) is None


def test_constant_suction_cups_veto_prevents_dragging_out():
    battle, user, target = build_battle(defender_ability="Suction Cups")
    assert battle.runEvent("DragOut", target, user, None) is False

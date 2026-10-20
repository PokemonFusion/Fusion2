"""OHKO accuracy, level, typing and Sturdy rules through real battle use."""

import logging
import random

import pytest

from .helpers import build_battle, load_modules


@pytest.fixture(autouse=True)
def quiet_log():
    logger = logging.getLogger("battle")
    old = logger.disabled
    logger.disabled = True
    yield
    logger.disabled = old


def strike(name, *, user_level=50, target_level=50, ability="No Guard", target_ability=None, types=None):
    from pokemon.battle.actions import Action, ActionType
    battle, user, target = build_battle(attacker_ability=ability, defender_ability=target_ability, defender_types=types)
    user.level, target.level = user_level, target_level
    battle.rng = random.Random(0)
    battle.use_move(Action(battle.participant_for(user), ActionType.MOVE,
                           battle.participant_for(target), load_modules()["BattleMove"](name), pokemon=user))
    assert not getattr(battle, "_callback_failures", [])
    return target.hp


@pytest.mark.parametrize("name", ["Fissure", "Guillotine", "Horn Drill", "Sheer Cold"])
def test_no_guard_ohko_faints_an_eligible_foe(name):
    assert strike(name) == 0


@pytest.mark.parametrize("name", ["Fissure", "Guillotine", "Horn Drill", "Sheer Cold"])
def test_no_guard_cannot_bypass_higher_level_or_sturdy(name):
    assert strike(name, user_level=49) == 200
    assert strike(name, target_ability="Sturdy") == 200


@pytest.mark.parametrize("name,types", [("Fissure", ["Flying"]), ("Guillotine", ["Ghost"]), ("Horn Drill", ["Ghost"]), ("Sheer Cold", ["Ice"])])
def test_no_guard_cannot_bypass_type_ohko_immunity(name, types):
    assert strike(name, types=types) == 200


def test_ohko_uses_its_accuracy_roll_without_no_guard():
    assert strike("Guillotine", ability=None) == 200


def test_fixed_ohko_damage_is_not_reduced_by_filter():
    assert strike("Fissure", target_ability="Filter", types=["Fire"]) == 0

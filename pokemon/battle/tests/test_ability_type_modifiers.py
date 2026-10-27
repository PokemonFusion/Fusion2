"""Super-effective and resisted ability modifiers observed failing live."""

import random

import pytest

from .helpers import build_battle, load_modules


def strike(ability, *, defending=False, types=("Water",), move="Thunder Shock"):
    """Keep the formula, named abilities and random rolls identical."""
    from pokemon.battle.actions import Action, ActionType

    battle, user, target = build_battle(
        attacker_ability="No Ability" if defending else ability,
        defender_ability=ability if defending else "No Ability",
        attacker_types=["Normal"], defender_types=list(types),
    )
    battle.rng = random.Random(0)
    action = Action(battle.participant_for(user), ActionType.MOVE,
                    battle.participant_for(target), load_modules()["BattleMove"](move), pokemon=user)
    battle.use_move(action)
    assert not getattr(battle, "_callback_failures", [])
    return target.max_hp - target.hp


@pytest.mark.parametrize("ability", ["Filter", "Solid Rock", "Prism Armor"])
def test_defensive_modifier_reduces_super_effective_damage_only(ability):
    ordinary = strike("No Ability", defending=True)
    assert strike(ability, defending=True) == int(ordinary * .75) > 0
    for types in (("Normal",), ("Electric",)):
        assert strike(ability, defending=True, types=types) == strike("No Ability", defending=True, types=types)


def test_neuroforce_increases_super_effective_damage_only():
    assert strike("Neuroforce") == int(strike("No Ability") * 1.25) > 0
    for types in (("Normal",), ("Electric",)):
        assert strike("Neuroforce", types=types) == strike("No Ability", types=types)


def test_tinted_lens_increases_resisted_damage_only():
    assert strike("Tinted Lens", types=("Electric",)) == strike("No Ability", types=("Electric",)) * 2 > 0
    for types in (("Normal",), ("Water",)):
        assert strike("Tinted Lens", types=types) == strike("No Ability", types=types)


@pytest.mark.parametrize("ability", ["Neuroforce", "Tinted Lens", "Filter", "Solid Rock", "Prism Armor"])
def test_type_modifier_does_not_bypass_a_ground_type_immunity(ability):
    assert strike(ability, defending=ability in {"Filter", "Solid Rock", "Prism Armor"}, types=("Ground",)) == 0

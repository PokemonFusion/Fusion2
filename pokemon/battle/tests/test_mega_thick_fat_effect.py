"""Actual source-stat reduction and owned-ability bypass for the Mega prerequisite."""

import random

import pytest

from .helpers import build_battle
from .test_pending_action_effects import action


def damage(move, control):
    """Execute a real hit with the same stats, typing and private damage seed."""
    battle, user, target = build_battle(
        attacker_ability="Mold Breaker" if control in {"mold", "shield"} else "No Ability",
        defender_ability="Thick Fat",
        defender_types=["Normal"],
    )
    target.ability_suppressed = control == "suppressed"
    if control == "shield":
        target.item = "Ability Shield"
    chosen = action(battle, user, target, move)
    if control == "move_bypass":
        chosen.move.raw["ignoreAbility"] = True
    battle.rng = random.Random(102)
    battle.use_move(chosen)
    return target.max_hp - target.hp


@pytest.mark.parametrize("move", ["Flamethrower", "Ice Beam", "Fire Punch", "Ice Punch"])
@pytest.mark.parametrize("control", ["suppressed", "mold", "move_bypass"])
def test_thick_fat_halves_real_fire_ice_offense_until_suppressed_or_bypassed(move, control):
    """Both physical and special reductions honor the existing bypass decision."""
    active, ignored = damage(move, "active"), damage(move, control)
    assert ignored > active * 1.8 > 0


@pytest.mark.parametrize("move", ["Flamethrower", "Ice Beam", "Water Gun", "Tackle"])
def test_ability_shield_retains_thick_fat_and_nonfire_ice_is_not_reduced(move):
    """Ability Shield prevents Mold Breaker; other move types never receive the reduction."""
    assert damage(move, "active") == damage(move, "shield")
    if move in {"Water Gun", "Tackle"}:
        assert damage(move, "active") == damage(move, "suppressed")

"""Named ability power hooks need their real owner, target and active state."""

import random

from .helpers import build_battle, load_modules


def strike(ability, *, defending=False, move="Shadow Ball", sand=False, active_slow_start=False):
    """Return the actual hit damage with identical formula inputs and RNG."""
    from pokemon.battle.actions import Action, ActionType

    battle, user, target = build_battle(
        attacker_ability="No Ability" if defending else ability,
        defender_ability=ability if defending else "No Ability",
        defender_types=["Rock"],
    )
    if sand:
        assert battle.setWeather("sandstorm", user)
    if active_slow_start:
        user.ability_state["slowstart"] = 5
    battle.rng = random.Random(0)
    action = Action(battle.participant_for(user), ActionType.MOVE,
                    battle.participant_for(target), load_modules()["BattleMove"](move), pokemon=user)
    battle.use_move(action)
    assert not getattr(battle, "_callback_failures", [])
    return target.max_hp - target.hp


def test_purifying_salt_uses_the_current_defenders_effect_state():
    ordinary = strike("No Ability", defending=True)
    first = strike("Purifying Salt", defending=True)
    second = strike("Purifying Salt", defending=True)
    assert first == second < ordinary
    assert first > 0


def test_purifying_salt_does_not_reduce_non_ghost_attacks_or_its_own_attack():
    assert strike("Purifying Salt", defending=True, move="Tackle") == strike("No Ability", defending=True, move="Tackle")
    assert strike("Purifying Salt") == strike("No Ability")


def test_sand_force_receives_the_attacker_alias_and_requires_sand_and_the_right_type():
    ordinary = strike("No Ability", move="Mud-Slap", sand=True)
    assert strike("Sand Force", move="Mud-Slap", sand=True) > ordinary > 0
    assert strike("Sand Force", move="Mud-Slap") == strike("No Ability", move="Mud-Slap")
    assert strike("Sand Force", move="Tackle", sand=True) == strike("No Ability", move="Tackle", sand=True)


def test_slow_start_counter_activates_the_nested_attack_modifier():
    ordinary = strike("No Ability", move="Tackle")
    actual = strike("Slow Start", move="Tackle", active_slow_start=True)
    assert 0 < actual < ordinary
    assert strike("Slow Start", move="Tackle") == ordinary


def test_slow_start_counts_down_once_per_turn_then_stops_halving_stats():
    from pokemon.battle.engine import _resolve_ability

    battle, user, _ = build_battle(attacker_ability="Slow Start")
    ability = _resolve_ability(user.ability)
    battle.singleEvent("Start", ability, user.ability_state, user)
    assert user.ability_state["slowstart"] == 5
    assert ability.call("onModifyAtk", 100, attacker=user) == 50
    for remaining in (4, 3, 2, 1, 0):
        battle.residual()
        assert user.ability_state["slowstart"] == remaining
    assert ability.call("onModifyAtk", 100, attacker=user) is None

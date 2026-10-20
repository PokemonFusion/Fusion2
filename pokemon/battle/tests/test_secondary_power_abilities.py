"""Real move execution must supply ability context and per-use secondary data."""

import copy
import random

from .helpers import build_battle, load_modules


def strike(ability, *, move="Tackle", after_target=False, guaranteed_secondary=False):
    """Use real action ordering and return observed damage and secondary state."""
    from pokemon.battle.actions import Action, ActionType
    from pokemon.dex import MOVEDEX

    battle, user, target = build_battle(attacker_ability=ability)
    battle.rng = random.Random(0)
    selected = load_modules()["BattleMove"](move)
    if guaranteed_secondary:
        selected.raw = copy.deepcopy(MOVEDEX[move.replace(" ", "").lower()].raw)
        selected.raw["secondary"]["chance"] = 100
    attack = Action(battle.participant_for(user), ActionType.MOVE,
                    battle.participant_for(target), selected, pokemon=user)
    splash = Action(battle.participant_for(target), ActionType.MOVE,
                    battle.participant_for(target), load_modules()["BattleMove"]("Splash"), pokemon=target)
    # Observe the guaranteed confusion before the control gets a later action:
    # confusion self-damage belongs to that later action, not this power check.
    actions = [attack] if guaranteed_secondary else [splash, attack] if after_target else [attack, splash]
    battle.execute_actions(actions)
    assert not getattr(battle, "_callback_failures", [])
    return target.max_hp - target.hp, target, selected


def test_analytic_gets_the_target_and_battle_context_when_attacking_last():
    ordinary, _, _ = strike("No Ability", after_target=True)
    boosted, _, _ = strike("Analytic", after_target=True)
    assert boosted > ordinary > 0


def test_analytic_does_not_boost_before_the_opponent_has_moved():
    ordinary, _, _ = strike("No Ability")
    actual, _, _ = strike("Analytic")
    assert actual == ordinary > 0


def test_sheer_force_increases_power_and_removes_the_actual_secondary():
    from pokemon.dex import MOVEDEX

    original = copy.deepcopy(MOVEDEX["waterpulse"].raw)
    ordinary, control, _ = strike("No Ability", move="Water Pulse", guaranteed_secondary=True)
    actual, target, selected = strike("Sheer Force", move="Water Pulse", guaranteed_secondary=True)
    assert actual > ordinary > 0
    assert "confusion" in control.volatiles
    assert "confusion" not in target.volatiles
    assert selected.sheer_force_boosted is True
    assert MOVEDEX["waterpulse"].raw == original


def test_sheer_force_keeps_moves_without_secondaries_unchanged():
    ordinary, _, _ = strike("No Ability")
    actual, _, selected = strike("Sheer Force")
    assert actual == ordinary > 0
    assert not getattr(selected, "sheer_force_boosted", False)

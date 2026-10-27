"""Qualifying incoming hits must reach one-turn side protection handlers."""

import random

import pytest

from .helpers import build_battle, load_modules


def use(battle, user, target, move):
    """Execute a real dex move through the ordinary action path."""
    from pokemon.battle.actions import Action, ActionType

    battle.rng = random.Random(0)
    action = Action(battle.participant_for(user), ActionType.MOVE,
                    battle.participant_for(target), load_modules()["BattleMove"](move), pokemon=user)
    battle.use_move(action)


@pytest.mark.parametrize("guard,attack", [("Quick Guard", "Quick Attack"), ("Wide Guard", "Surf")])
def test_side_protection_blocks_its_qualifying_attack(guard, attack):
    battle, user, foe = build_battle()
    use(battle, user, user, guard)
    use(battle, foe, user, attack)
    assert user.hp == user.max_hp


@pytest.mark.parametrize("guard,attack", [("Quick Guard", "Tackle"), ("Wide Guard", "Water Gun"), ("Crafty Shield", "Tackle")])
def test_side_protection_does_not_block_a_nonqualifying_attack(guard, attack):
    battle, user, foe = build_battle()
    use(battle, user, user, guard)
    use(battle, foe, user, attack)
    assert user.hp < user.max_hp


def test_crafty_shield_blocks_the_opposing_stat_drop():
    battle, user, foe = build_battle()
    use(battle, user, user, "Crafty Shield")
    use(battle, foe, user, "Growl")
    assert all(stage == 0 for stage in user.boosts.values())


def test_quick_guard_expires_before_the_following_turn():
    battle, user, foe = build_battle()
    use(battle, user, user, "Quick Guard")
    battle.residual()
    use(battle, foe, user, "Quick Attack")
    assert user.hp < user.max_hp


def test_a_finite_screen_expires_and_cleans_up_the_legacy_screen_flag():
    battle, user, _ = build_battle()
    use(battle, user, user, "Reflect")
    for _ in range(4):
        battle.residual()
        assert user.side.screens.get("reflect")
    battle.residual()
    assert "reflect" not in user.side.conditions
    assert "reflect" not in user.side.screens


def test_a_permanent_hazard_does_not_expire_with_finite_side_effects():
    battle, user, foe = build_battle()
    use(battle, user, foe, "Spikes")
    for _ in range(8):
        battle.residual()
    assert "spikes" in foe.side.conditions

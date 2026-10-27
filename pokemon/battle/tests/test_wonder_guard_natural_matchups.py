"""Natural Bug/Ghost Wonder Guard matchups reproduced through ordinary actions."""

import random

import pytest

from .helpers import build_battle, load_modules


def strike(name, *, ability="Wonder Guard", types=("Bug", "Ghost")):
    """Compare the same move, native defending types and private random stream."""
    from pokemon.battle.actions import Action, ActionType

    battle, user, target = build_battle(
        attacker_ability="No Ability", defender_ability=ability,
        attacker_types=["Normal"], defender_types=list(types),
    )
    battle.rng = random.Random(0)
    action = Action(battle.participant_for(user), ActionType.MOVE,
                    battle.participant_for(target), load_modules()["BattleMove"](name), pokemon=user)
    battle.use_move(action)
    assert not getattr(battle, "_callback_failures", [])
    return target.max_hp - target.hp, target.boosts


@pytest.mark.parametrize("name", ["Ember", "Gust", "Rock Throw", "Lick", "Bite"])
def test_wonder_guard_allows_each_native_super_effective_type(name):
    ordinary, _ = strike(name, ability="No Ability")
    guarded, _ = strike(name)
    assert guarded == ordinary > 0


@pytest.mark.parametrize("name", ["Water Gun", "Thunder Shock"])
def test_wonder_guard_blocks_native_neutral_damaging_hits(name):
    assert strike(name, ability="No Ability")[0] > 0
    assert strike(name)[0] == 0


def test_wonder_guard_preserves_native_normal_immunity():
    assert strike("Tackle", ability="No Ability")[0] == strike("Tackle")[0] == 0


def test_wonder_guard_allows_reflectable_status_moves():
    ordinary = strike("Growl", ability="No Ability")[1]
    guarded = strike("Growl")[1]
    assert guarded == ordinary
    assert guarded.get("atk", guarded.get("attack")) == -1


def test_wonder_guard_preserves_struggle_exception_on_hittable_target():
    # The ordinary engine currently mishandles Struggle's typeless Ghost
    # interaction independently. Keep that recorded defect separate while
    # checking Wonder Guard's own exception on an otherwise hittable target.
    ordinary, _ = strike("Struggle", ability="No Ability", types=("Normal",))
    guarded, _ = strike("Struggle", types=("Normal",))
    assert guarded == ordinary > 0

"""Modern repeated Protect chance, reset and checkpoint policy before Z-Protect."""

import random
import pytest

from .test_diagnosed_item_effects import native_battle
from .test_pending_action_effects import action


class ConstantRoll(random.Random):
    """Expose exact legal probability boundaries without replacing the effect."""

    def __init__(self, value):
        super().__init__(1)
        self.value = value

    def random(self):
        return self.value


def test_second_protect_can_fail_at_half_roll():
    """A second consecutive use has one-third success, rather than guaranteed success."""
    battle, user, foe = native_battle("Pelipper")
    battle.rng = ConstantRoll(0.5)
    move = action(battle, user, user, "Protect").move
    assert battle._passes_stall_move(user, move)
    assert not battle._passes_stall_move(user, move)


def test_successful_protect_denominators_are_three_powers_and_capped():
    """Actual consecutive attempts advance 3/9/27/81/243/729 and stay bounded."""
    battle, user, foe = native_battle("Pelipper")
    battle.rng = ConstantRoll(0)
    move = action(battle, user, user, "Protect").move
    for denominator in [3, 9, 27, 81, 243, 729, 729]:
        assert battle._passes_stall_move(user, move)
        assert user.volatiles["stall"]["counter"] == denominator


@pytest.mark.parametrize("reset", ["failure", "other-move", "gap", "switch"])
def test_stall_resets_through_actual_runtime_boundaries(reset):
    """A failed attempt, different move, elapsed turn or switch cannot keep a streak."""
    battle, user, foe = native_battle("Pelipper")
    battle.rng = ConstantRoll(0.5)
    move = action(battle, user, user, "Protect").move
    assert battle._passes_stall_move(user, move)
    if reset == "failure":
        assert not battle._passes_stall_move(user, move)
    elif reset == "other-move":
        assert battle._passes_stall_move(user, action(battle, user, foe, "Growl").move)
    elif reset == "gap":
        battle.end_turn()
        battle.end_turn()
    else:
        battle.on_switch_out(user)
    assert "stall" not in user.volatiles
    assert battle._passes_stall_move(user, move)
    assert user.volatiles["stall"]["counter"] == 3


@pytest.mark.parametrize("counter,expected", [(1, 3), (2, 9), (4, 27), (256, 729), (729, 729)])
def test_legacy_counter_snapshot_keeps_a_conservative_streak(counter, expected):
    """Known former powers convert once; a legacy snapshot cannot grant a free first use."""
    from pokemon.dex.functions.conditions_funcs import Stall

    battle, user, foe = native_battle("Pelipper")
    user.volatiles["stall"] = {"counter": counter}
    assert Stall().onStallMove(user) == 1 / expected
    assert user.volatiles["stall"]["version"] == 2
    assert Stall().onStallMove(user) == 1 / expected


@pytest.mark.parametrize("counter", [None, 3.0, True, [], {}, "3"])
def test_invalid_new_counter_cannot_grant_a_free_protection_attempt(counter):
    """Malformed primitive checkpoint counters retain the conservative cap."""
    from pokemon.dex.functions.conditions_funcs import Stall

    battle, user, foe = native_battle("Pelipper")
    user.volatiles["stall"] = {"version": 2, "counter": counter}
    assert Stall().onStallMove(user) == 1 / 729


@pytest.mark.parametrize(
    "state", [{}, False, {"version": 3, "counter": 3}, {"version": 2.0, "counter": 3}]
)
def test_unknown_or_empty_stall_checkpoint_is_conservative(state):
    """An existing malformed state differs from an absent legitimate first use."""
    from pokemon.dex.functions.conditions_funcs import Stall

    battle, user, foe = native_battle("Pelipper")
    user.volatiles["stall"] = state
    assert Stall().onStallMove(user) == 1 / 729
    assert user.volatiles["stall"]["version"] == 2
    assert Stall().onStallMove(user) == 1 / 729


def test_protect_real_damage_and_reconstructed_repeat_failure():
    """The first actual shield blocks damage; the next restored attempt can fail."""
    battle, user, foe = native_battle("Pelipper")
    battle.rng = ConstantRoll(0.5)
    battle.use_move(action(battle, user, user, "Protect"))
    hp = user.hp
    battle.use_move(action(battle, foe, user, "Tackle"))
    assert user.hp == hp
    battle.residual()
    battle.end_turn()
    user = type(user).from_dict(user.to_dict())
    user.battle = battle
    battle.participants[0].pokemons = [user]
    battle.participants[0].active = [user]
    battle.use_move(action(battle, user, user, "Protect"))
    battle.use_move(action(battle, foe, user, "Tackle"))
    assert user.hp < hp and "stall" not in user.volatiles

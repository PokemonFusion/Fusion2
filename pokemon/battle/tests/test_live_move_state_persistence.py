"""Observed special moves must change real PP, stats and canonical side state."""

import logging
import random
from types import SimpleNamespace

import pytest

from .helpers import build_battle, load_modules


@pytest.fixture(autouse=True)
def quiet_offline_battle_log():
    """Keep this diagnostic process separate from live acceptance logs."""
    logger = logging.getLogger("battle")
    disabled = logger.disabled
    logger.disabled = True
    yield
    logger.disabled = disabled


def use(battle, user, target, name):
    """Exercise the real named move path with reproducible damage rolls."""
    from pokemon.battle.actions import Action, ActionType

    battle.rng = random.Random(0)
    battle.use_move(Action(battle.participant_for(user), ActionType.MOVE,
                           battle.participant_for(target), load_modules()["BattleMove"](name), pokemon=user))
    assert not getattr(battle, "_callback_failures", [])


class Slots:
    """Keep the owned slot independently observable from the battle move."""

    def __init__(self, pp):
        self.saved = []
        self.slot = SimpleNamespace(move=SimpleNamespace(name="Tackle"), current_pp=pp)
        self.slot.save = lambda **kwargs: self.saved.append(self.slot.current_pp)

    def all(self):
        """Return only the independently stored selected move slot."""
        return [self.slot]


@pytest.mark.parametrize("remaining,expected", [(10, 6), (2, 0), (0, 0)])
def test_spite_reduces_the_owned_and_cached_pp_without_going_negative(remaining, expected):
    battle, user, target = build_battle()
    slots = target.activemoveslot_set = Slots(remaining)
    cached = load_modules()["Move"]("Tackle")
    cached.pp = remaining
    target.moves = [cached]
    target.last_move = load_modules()["BattleMove"]("Tackle", pp=remaining)
    use(battle, user, target, "Spite")
    assert slots.slot.current_pp == cached.pp == target.last_move.pp == expected
    assert slots.saved == ([expected] if remaining else [])


def test_spite_without_a_previous_move_does_not_change_an_owned_slot():
    battle, user, target = build_battle()
    slots = target.activemoveslot_set = Slots(10)
    use(battle, user, target, "Spite")
    assert slots.slot.current_pp == 10 and not slots.saved


def differing_stats():
    """Prepare independent unboosted stats for averaging and order assertions."""
    battle, user, target = build_battle()
    target.base_stats.attack = 60
    target.base_stats.special_attack = 80
    target.base_stats.defense = 200
    target.base_stats.special_defense = 160
    target.base_stats.speed = 50
    return battle, user, target


@pytest.mark.parametrize("name,values", [("Guard Split", {"defense": 160, "special_defense": 140}),
                                        ("Power Split", {"attack": 90, "special_attack": 100})])
def test_split_moves_change_the_stats_used_by_real_damage_and_survive_a_checkpoint(name, values):
    from pokemon.battle.utils import get_modified_stat

    battle, user, target = differing_stats()
    use(battle, user, target, name)
    for pokemon in (user, target):
        for stat, expected in values.items():
            assert get_modified_stat(pokemon, stat) == expected
        restored = load_modules()["Pokemon"].from_dict(pokemon.to_dict())
        for stat, expected in values.items():
            assert get_modified_stat(restored, stat) == expected


def test_power_split_averages_unboosted_stats_then_preserves_existing_stages():
    from pokemon.battle.utils import get_modified_stat

    battle, user, target = differing_stats()
    user.boosts["attack"] = 2
    use(battle, user, target, "Power Split")
    assert get_modified_stat(user, "attack") == 180
    assert get_modified_stat(target, "attack") == 90


def test_split_stats_reset_independently_when_each_holder_leaves():
    from pokemon.battle.utils import get_modified_stat

    battle, user, target = differing_stats()
    use(battle, user, target, "Guard Split")
    battle.on_switch_out(user)
    assert get_modified_stat(user, "defense") == 120
    assert get_modified_stat(target, "defense") == 160
    battle.on_switch_out(target)
    assert get_modified_stat(target, "defense") == 200


def test_split_stats_survive_the_next_real_turn_boundary():
    from pokemon.battle.utils import get_modified_stat

    battle, user, target = differing_stats()
    use(battle, user, target, "Guard Split")
    battle.run_after_switch()
    assert get_modified_stat(user, "defense") == get_modified_stat(target, "defense") == 160


def test_last_resort_remembers_the_previous_turns_attempted_move():
    battle, user, target = build_battle()
    user.moves = [load_modules()["Move"]("Last Resort"), load_modules()["Move"]("Splash")]
    use(battle, user, user, "Splash")
    battle.run_after_switch()
    use(battle, user, target, "Last Resort")
    assert target.hp < target.max_hp


@pytest.mark.parametrize("name,relation", [("Guard Split", "greater"), ("Power Split", "less")])
def test_split_changes_the_damage_of_the_next_real_attack(name, relation):
    battle, user, target = differing_stats()
    use(battle, user, target, "Tackle")
    previous = target.max_hp - target.hp
    target.hp = target.max_hp
    use(battle, user, target, name)
    use(battle, user, target, "Tackle")
    actual = target.max_hp - target.hp
    assert (actual > previous) if relation == "greater" else (actual < previous)


def test_speed_swap_changes_the_actual_action_order_and_resets_on_leaving():
    from pokemon.battle.actions import Action, ActionType
    from pokemon.battle.utils import get_modified_stat

    battle, user, target = differing_stats()
    use(battle, user, target, "Speed Swap")
    assert get_modified_stat(user, "speed") == 50
    assert get_modified_stat(target, "speed") == 120
    actions = [Action(battle.participant_for(p), ActionType.MOVE, move=load_modules()["BattleMove"]("Tackle"), pokemon=p)
               for p in (user, target)]
    assert battle.order_actions(actions)[0].pokemon is target
    battle.on_switch_out(user)
    battle.on_switch_out(target)
    assert get_modified_stat(user, "speed") == 120
    assert get_modified_stat(target, "speed") == 50


def test_court_change_swaps_canonical_conditions_without_resetting_duration_or_swapping_guards():
    battle, user, target = build_battle()
    use(battle, user, user, "Light Screen")
    use(battle, target, target, "Reflect")
    use(battle, target, target, "Tailwind")
    use(battle, user, target, "Spikes")
    battle.residual()
    use(battle, target, target, "Quick Guard")
    use(battle, user, target, "Court Change")
    assert "reflect" in user.side.conditions and "reflect" not in target.side.conditions
    assert user.side.conditions["reflect"]["duration"] == 4
    assert user.side.conditions["tailwind"]["duration"] == 3
    assert "spikes" in user.side.conditions and "spikes" not in target.side.conditions
    assert "lightscreen" in target.side.conditions and "lightscreen" not in user.side.conditions
    assert "quickguard" in target.side.conditions and "quickguard" not in user.side.conditions


def test_court_change_updates_the_screen_that_real_damage_uses():
    battle, user, target = build_battle()
    use(battle, target, target, "Reflect")
    use(battle, user, target, "Tackle")
    screened = target.max_hp - target.hp
    target.hp = target.max_hp
    use(battle, user, target, "Court Change")
    use(battle, user, target, "Tackle")
    assert target.max_hp - target.hp > screened

"""Weather chip must use actual types and ordinary immunity/damage events."""

import random

import pytest

from .helpers import build_battle, load_modules


@pytest.mark.parametrize("weather", ["Sandstorm", "Hail"])
def test_overcoat_and_magic_guard_prevent_weather_chip(weather):
    from pokemon.dex.functions import conditions_funcs

    handler = getattr(conditions_funcs, weather)()
    for ability in ("Overcoat", "Magic Guard"):
        battle, _, holder = build_battle(defender_ability=ability)
        assert handler.onWeather(holder) == 0
        assert holder.hp == holder.max_hp


@pytest.mark.parametrize("types", [["Rock"], ["Ground"], ["Steel"], ["Water", "Rock"]])
def test_sandstorm_uses_the_real_battle_type_list(types):
    from pokemon.dex.functions.conditions_funcs import Sandstorm

    _, _, holder = build_battle(defender_types=types)
    assert Sandstorm().onWeather(holder) == 0
    assert holder.hp == holder.max_hp


def test_hail_preserves_ice_immunity_and_hurts_an_unprotected_normal_type():
    from pokemon.dex.functions.conditions_funcs import Hail

    _, ordinary, ice = build_battle(defender_types=["Ice"])
    assert Hail().onWeather(ice) == 0
    assert Hail().onWeather(ordinary) == ordinary.max_hp // 16
    assert ordinary.hp == ordinary.max_hp - ordinary.max_hp // 16


def test_safety_goggles_weather_immunity_uses_the_held_item_event():
    from pokemon.dex.functions.conditions_funcs import Sandstorm

    _, _, holder = build_battle()
    holder.item = "Safety Goggles"
    assert Sandstorm().onWeather(holder) == 0
    assert holder.hp == holder.max_hp


def test_magic_guard_allows_direct_move_damage_instead_of_granting_invulnerability():
    from pokemon.battle.actions import Action, ActionType

    losses = []
    for ability in ("No Ability", "Magic Guard"):
        battle, user, holder = build_battle(defender_ability=ability)
        battle.rng = random.Random(0)
        action = Action(battle.participant_for(user), ActionType.MOVE,
                        battle.participant_for(holder), load_modules()["BattleMove"]("Tackle"), pokemon=user)
        battle.use_move(action)
        losses.append(holder.max_hp - holder.hp)
    assert losses[0] == losses[1] > 0

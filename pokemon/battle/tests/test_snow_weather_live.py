"""The local dex's snow weather ID must have a complete field handler."""

from types import SimpleNamespace

import pytest

from .helpers import build_battle


def test_snow_can_start_and_expires_after_five_turns_without_hail_damage():
    battle, user, target = build_battle()
    assert battle.setWeather("snow", user)
    assert battle.field.weather == "snow"
    for _ in range(4):
        battle.residual()
        battle.end_turn()
        assert battle.field.weather == "snow"
        assert user.hp == user.max_hp and target.hp == target.max_hp
    battle.residual()
    battle.end_turn()
    assert not battle.field.weather
    assert "snow" not in battle.field.pseudo_weather


@pytest.mark.parametrize("item", ["Icy Rock", SimpleNamespace(name="Icy Rock")])
def test_icy_rock_extends_snow_to_eight_turns(item):
    battle, user, _ = build_battle()
    user.item = item
    assert battle.setWeather("snow", user)
    assert battle.field.pseudo_weather["snow"]["duration"] == 8


def test_snow_defense_hook_uses_real_types_and_excludes_non_ice_species():
    battle, user, target = build_battle(attacker_types=["Ice"], defender_types=["Water"])
    assert battle.setWeather("snow", user)
    assert battle.runEvent("ModifyDef", user, target, None, 100) == 150
    assert battle.runEvent("ModifyDef", target, user, None, 100) == 100


def test_snow_warning_starts_the_same_weather_as_the_snow_move():
    from pokemon.battle.engine import _resolve_ability

    battle, user, _ = build_battle(attacker_ability="Snow Warning")
    battle.singleEvent("Start", _resolve_ability(user.ability), user.ability_state, user)
    assert battle.field.weather == "snow"
    assert not getattr(battle, "_callback_failures", [])


def test_snow_warning_accepts_the_registered_startup_dispatch_context():
    battle, user, _ = build_battle(attacker_ability="Snow Warning")
    battle.register_handlers(user)
    battle.dispatcher.dispatch("start", pokemon=user, battle=battle)
    assert battle.field.weather == "snow"

"""Ordinary Roost typing and weather-aware Synthesis prerequisites (#913)."""

import pytest

from .test_diagnosed_item_effects import native_battle
from .test_pending_action_effects import action


@pytest.mark.parametrize(
    "weather,numerator,denominator",
    [(None, 1, 2), ("sunnyday", 2, 3), ("raindance", 1, 4), ("sandstorm", 1, 4), ("snow", 1, 4)],
)
def test_synthesis_weather_healing(weather, numerator, denominator):
    """Normalized ordinary weather must reach its actual healing fraction."""
    battle, user, foe = native_battle("Bulbasaur", hp_fraction=0.1)
    if weather:
        battle.setWeather(weather, source=foe)
    before = user.hp
    battle.use_move(action(battle, user, user, "Synthesis"))
    assert user.hp == min(user.max_hp, before + user.max_hp * numerator // denominator)


@pytest.mark.parametrize("finish", ["residual", "switch", "faint", "end", "checkpoint"])
def test_roost_lifecycle_restores_real_native_typing(finish):
    """Temporary state survives reconstruction and ends through each real hook."""
    battle, user, foe = native_battle("Pidgeot", hp_fraction=0.25)
    original = list(user.types)
    battle.use_move(action(battle, user, user, "Roost"))
    assert user.types == ["Normal"]
    if finish == "checkpoint":
        user = type(user).from_dict(user.to_dict())
        user.battle = battle
        battle.participants[0].pokemons = [user]
        battle.participants[0].active = [user]
        assert user.types == ["Normal"] and user.volatiles["roost"]["original_types"] == original
    if finish in {"residual", "checkpoint"}:
        battle.residual()
        battle.end_turn()
    elif finish == "switch":
        battle.on_switch_out(user)
    elif finish == "faint":
        user.hp = 0
        battle.on_faint(user)
    else:
        battle.restore_transforms()
    assert user.types == original and "roost" not in user.volatiles


@pytest.mark.parametrize("mode", ["full", "blocked", "tera"])
def test_roost_does_not_change_type_without_eligible_useful_healing(mode):
    """A failed heal or fixed Tera defensive type never loses Flying."""
    battle, user, foe = native_battle("Pidgeot", hp_fraction=1 if mode == "full" else 0.25)
    original = list(user.types)
    if mode == "blocked":
        battle.apply_volatile_status(user, "healblock", source=foe)
    elif mode == "tera":
        user.terastallized = True  # Explicit offline fixed-type adapter.
    before = user.hp
    battle.use_move(action(battle, user, user, "Roost"))
    assert user.types == original and "roost" not in user.volatiles
    if mode != "tera":
        assert user.hp == before


def test_roost_ground_hit_window_and_later_soak_are_not_overwritten():
    """Ground damage witnesses the removed immunity; later independent typing wins."""
    battle, user, foe = native_battle("Pidgeot", hp_fraction=0.25)
    hp = user.hp
    battle.use_move(action(battle, foe, user, "Mud-Slap"))
    assert user.hp == hp
    battle.use_move(action(battle, user, user, "Roost"))
    hp = user.hp
    battle.use_move(action(battle, foe, user, "Mud-Slap"))
    assert user.hp < hp
    battle.use_move(action(battle, foe, user, "Soak"))
    assert user.types == ["Water"]
    battle.end_turn()
    assert user.types == ["Water"] and "roost" not in user.volatiles


def test_pure_flying_roost_uses_normal_until_end_of_turn():
    """The modern-generation fallback cannot leave an empty type vector."""
    battle, user, foe = native_battle("Tornadus", hp_fraction=0.25)
    assert user.types == ["Flying"]
    battle.use_move(action(battle, user, user, "Roost"))
    assert user.types == ["Normal"]
    battle.end_turn()
    assert user.types == ["Flying"]


@pytest.mark.parametrize(
    "weather,item,ability,divisor",
    [
        ("sunnyday", "Utility Umbrella", "No Ability", 2),
        ("raindance", "Utility Umbrella", "No Ability", 2),
        ("sandstorm", "Utility Umbrella", "No Ability", 4),
        ("sunnyday", "", "Cloud Nine", 2),
        ("raindance", "", "Air Lock", 2),
    ],
)
def test_synthesis_uses_actual_holder_weather_suppression(weather, item, ability, divisor):
    """Weather stays installed while the actual holder or ability suppresses it."""
    battle, user, foe = native_battle("Bulbasaur", item, hp_fraction=0.1)
    foe.ability = ability  # Labelled offline suppression adapter.
    battle.setWeather(weather, source=foe)
    before = user.hp
    battle.use_move(action(battle, user, user, "Synthesis"))
    assert user.hp == min(user.max_hp, before + user.max_hp // divisor)


@pytest.mark.parametrize("mode", ["full", "blocked"])
def test_synthesis_respects_full_hp_and_heal_block(mode):
    """The ordinary heal uses common prevention rather than assigning HP directly."""
    battle, user, foe = native_battle("Bulbasaur", hp_fraction=1 if mode == "full" else 0.1)
    if mode == "blocked":
        battle.apply_volatile_status(user, "healblock", source=foe)
    before = user.hp
    battle.use_move(action(battle, user, user, "Synthesis"))
    assert user.hp == before

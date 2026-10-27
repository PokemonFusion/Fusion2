"""Zen Mode must change forms without replacing or recursively ending itself."""

import pytest

from .helpers import build_battle


def carrier(name, hp):
    """Build a real battle carrier whose original form may itself be Zen."""
    battle, pokemon, _ = build_battle(attacker_ability="Zen Mode")
    pokemon.species = pokemon.base_species = pokemon.name = name
    pokemon.hp = hp
    return battle, pokemon


def event(battle, pokemon, name):
    """Use the same single-event ability lifecycle path as the live engine."""
    from pokemon.battle.engine import _resolve_ability

    battle.singleEvent(name, _resolve_ability(pokemon.ability), pokemon.ability_state, pokemon)


@pytest.mark.parametrize("base", ["Darmanitan", "Darmanitan-Galar"])
def test_full_health_prepared_zen_form_reverts_without_recursive_ability_end(base):
    battle, pokemon = carrier(base + "-Zen", 200)
    event(battle, pokemon, "Residual")
    assert str(pokemon.species) == base
    assert getattr(pokemon.ability, "name", pokemon.ability) == "Zen Mode"
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("base", ["Darmanitan", "Darmanitan-Galar"])
def test_low_hp_changes_then_healing_reverts_and_keeps_the_hidden_ability(base):
    battle, pokemon = carrier(base, 100)
    event(battle, pokemon, "Residual")
    assert str(pokemon.species) == base + "-Zen"
    assert getattr(pokemon.ability, "name", pokemon.ability) == "Zen Mode"
    pokemon.hp = 101
    event(battle, pokemon, "Residual")
    assert str(pokemon.species) == base
    assert getattr(pokemon.ability, "name", pokemon.ability) == "Zen Mode"
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("base", ["Darmanitan", "Darmanitan-Galar"])
def test_ending_zen_mode_returns_to_the_regional_base_even_at_low_hp(base):
    battle, pokemon = carrier(base + "-Zen", 80)
    event(battle, pokemon, "End")
    assert str(pokemon.species) == base
    assert not getattr(battle, "_callback_failures", [])


def test_unrelated_species_and_healthy_base_do_not_change_form():
    for name in ("Mew", "Darmanitan", "Darmanitan-Galar"):
        battle, pokemon = carrier(name, 200)
        event(battle, pokemon, "Residual")
        assert str(pokemon.species) == name
        assert pokemon.ability == "Zen Mode"
        assert not getattr(battle, "_callback_failures", [])

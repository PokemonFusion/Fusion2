"""Held-item form entry must install the real ability, not a dex placeholder."""

import pytest

from pokemon.battle.effect_context import EffectContext
from pokemon.dex import ABILITYDEX
from pokemon.names import resolve_dex_entry

from .test_diagnosed_item_effects import attack, native_battle


@pytest.mark.parametrize("species,item,ability", (
    ("Dialga", "Adamant Crystal", "Pressure"),
    ("Palkia", "Lustrous Globe", "Pressure"),
    ("Giratina", "Griseous Core", "Levitate"),
    ("Kyogre", "Blue Orb", "Primordial Sea"),
    ("Groudon", "Red Orb", "Desolate Land"),
    ("Zacian", "Rusted Sword", "Intrepid Sword"),
    ("Zamazenta", "Rusted Shield", "Dauntless Shield"),
))
def test_item_form_installs_canonical_ability_callbacks(species, item, ability):
    """Native forms retain a canonical callback object before any restoration."""
    battle, holder, _ = native_battle(species, item=item)
    canonical = resolve_dex_entry(ABILITYDEX, ability)
    assert EffectContext.ability(holder).raw is canonical.raw
    assert EffectContext.ability(holder).name == canonical.raw["name"]
    if ability in {"Primordial Sea", "Desolate Land"}:
        battle.on_enter_battle(holder)
        assert battle.field.weather == EffectContext.key(ability)
    if ability == "Intrepid Sword":
        assert holder.boosts["attack"] == 1
    if ability == "Dauntless Shield":
        assert holder.boosts["defense"] == 1
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("species,item", (("Dialga", "Adamant Crystal"), ("Palkia", "Lustrous Globe")))
def test_pressure_charges_actual_source_pp_immediately_after_item_entry(species, item):
    """Real targeting/events charge two PP without needing a checkpoint first."""
    battle, holder, source = native_battle(species, item=item, foe="Mew")
    from pokemon.battle.battledata import Move
    source.moves = [Move("Thief")]
    source.moves[0].pp = 10
    damage, _ = attack(battle, source, holder, "Thief")
    assert damage > 0
    assert source.moves[0].pp == 8


@pytest.mark.parametrize("species,item", (("Kyogre", "Blue Orb"), ("Groudon", "Red Orb")))
def test_primal_weather_ends_with_its_real_holder(species, item):
    """A form ability's ordinary End hook cannot receive an opponent as battle."""
    battle, holder, source = native_battle(species, item=item)
    assert battle.weather_state["source"] is holder
    battle.set_ability(holder, "No Ability", source=source, is_transform=True)
    assert not battle.field.weather
    assert not getattr(battle, "_callback_failures", [])

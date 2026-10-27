"""Regressions for item forms changing foreign holders or restoring abilities."""

from types import SimpleNamespace

import pytest

from pokemon import dex
from pokemon.helpers.pokemon_helpers import get_max_hp, get_stats
from pokemon.names import resolve_dex_entry

from .test_diagnosed_item_effects import native_battle

FORM_ITEMS = sorted({entry.raw["name"]: entry for entry in dex.ITEMDEX.values()
                     if entry.raw.get("forcedForme")}.items())


def identity(pokemon):
    """Include the form's stats and ability so a disguised mutation cannot pass."""
    return (str(pokemon.species), list(pokemon.types), pokemon.ability,
            pokemon.max_hp, pokemon.hp, vars(pokemon.base_stats).copy())


@pytest.mark.parametrize("item,entry", FORM_ITEMS, ids=[row[0] for row in FORM_ITEMS])
def test_foreign_holder_keeps_species_ability_types_and_stats_on_assignment_and_entry(item, entry):
    battle, holder, _ = native_battle(ability="Synchronize")
    initial = identity(holder)
    assert battle.set_item(holder, entry)
    assert identity(holder) == initial
    battle.on_enter_battle(holder)
    assert identity(holder) == initial
    assert holder.item.raw["name"] == item
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("item,entry", FORM_ITEMS, ids=[row[0] for row in FORM_ITEMS])
def test_matching_native_holder_still_enters_its_calculated_item_form(item, entry):
    target = entry.raw["forcedForme"]
    form = resolve_dex_entry(dex.POKEDEX, target)
    species = form.raw["baseSpecies"]
    base = resolve_dex_entry(dex.POKEDEX, species)
    ability = str(next(iter(base.raw["abilities"].values())))
    battle, holder, _ = native_battle(species, ability=ability)
    assert battle.set_item(holder, entry)
    battle.on_enter_battle(holder)
    assert str(holder.species) == target
    assert holder.types == form.raw["types"]
    calculated = SimpleNamespace(species=target, level=holder.level, ivs=holder.ivs,
                                 evs=holder.evs, nature=holder.nature)
    assert holder.max_hp == get_max_hp(calculated)
    assert vars(holder.base_stats) == get_stats(calculated)
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("species,item", [("Arceus", "Flame Plate"), ("Silvally", "Fire Memory")])
def test_form_item_does_not_install_the_missing_native_ability(species, item):
    battle, holder, _ = native_battle(species, ability="No Ability")
    initial = identity(holder)
    assert battle.set_item(holder, resolve_dex_entry(dex.ITEMDEX, item))
    battle.on_enter_battle(holder)
    assert identity(holder) == initial


@pytest.mark.parametrize("species,item", [("Arceus", "Flame Plate"), ("Giratina", "Griseous Core"),
                                         ("Kyogre", "Blue Orb"), ("Zacian", "Rusted Sword")])
def test_copied_native_appearance_cannot_unlock_another_species_item_form(species, item):
    battle, holder, _ = native_battle(ability="Synchronize")
    holder.species = species
    holder.name = species
    holder.transformed = True
    initial = identity(holder)
    assert battle.set_item(holder, resolve_dex_entry(dex.ITEMDEX, item))
    battle.on_enter_battle(holder)
    assert identity(holder) == initial


@pytest.mark.parametrize("species,item", [("Kyogre", "Blue Orb"), ("Groudon", "Red Orb")])
def test_foreign_nickname_cannot_unlock_primal_callback(species, item):
    battle, holder, _ = native_battle(ability="Synchronize")
    holder.name = species
    initial = identity(holder)
    assert battle.set_item(holder, resolve_dex_entry(dex.ITEMDEX, item))
    battle.on_enter_battle(holder)
    assert identity(holder) == initial


def test_native_form_matching_uses_species_instead_of_nickname():
    battle, holder, _ = native_battle("Giratina", ability="Pressure")
    holder.name = "Giratina-Origin"
    assert battle.set_item(holder, resolve_dex_entry(dex.ITEMDEX, "Griseous Core"))
    assert str(holder.species) == "Giratina-Origin"


def test_untransformed_foreign_base_cannot_unlock_a_native_item_form():
    battle, holder, _ = native_battle("Giratina", ability="Pressure")
    holder.base_species = "Ditto"
    initial = identity(holder)
    assert battle.set_item(holder, resolve_dex_entry(dex.ITEMDEX, "Griseous Core"))
    assert identity(holder) == initial

"""Exact Peat Block equivalent; no full-moon or generic other-rule bypass."""

from types import SimpleNamespace

import pytest

from pokemon.data.evolution import (
    EvolutionContext, attempt_evolution, get_evolution, get_evolution_items,
    lookup_species,
)
from pokemon.evolution_items import PeatBlockEvolution
from pokemon.items import get_gameplay_item
from pokemon.middleware import get_item_by_name


@pytest.mark.parametrize("query", ["Peat Block", "PEATBLOCK", "peat-block"])
def test_complete_item_lookup_and_explicit_bag_use(query):
    """The normal rule requires a complete item; no lunar context is asserted."""
    item = get_gameplay_item(query)
    assert get_item_by_name(query)[1] is item
    assert item.name == "Peat Block" and item.category == "Evolution Items"
    assert item.price == 10000 and "+evolve" in item.desc
    assert "Peat Block" in get_evolution_items()
    assert get_evolution("Ursaring", level=1, item=query) == "Ursaluna"
    assert not EvolutionContext().meets(PeatBlockEvolution.condition)


@pytest.mark.parametrize("item", [None, "", "Peat", "Block", "Peat Block full moon", "Moon Stone"])
def test_missing_partial_and_wrong_bag_items_fail_closed(item):
    """Night, a held copy and unrelated context do not replace item input."""
    context = EvolutionContext(held_item="Peat Block", time="night", region="Hisui")
    assert get_evolution("Ursaring", level=100, item=item, context=context) is None


@pytest.mark.parametrize("time", ["", "day", "night", "full moon"])
def test_selected_equivalent_has_no_time_predicate_and_retains_everstone(time):
    """No environmental value asserts lunar evidence or overrides Everstone."""
    assert get_evolution("Ursaring", level=1, item="Peat Block", context=EvolutionContext(time=time)) == "Ursaluna"
    assert get_evolution("Ursaring", level=100, item="Peat Block",
                         context=EvolutionContext(time=time, held_item="Everstone")) is None


@pytest.mark.parametrize("source,target", [
    ("Teddiursa", "Ursaluna"), ("Pikachu", "Ursaluna"),
    ("Ursaluna", "Ursaluna-Bloodmoon"), ("Ursaring", "Ursaluna-Bloodmoon"),
    ("Ursaring", "Ursal"), ("Ursaring-Hisui", "Ursaluna"),
    ("Ursaluna-Bloodmoon", "Ursaluna"),
])
def test_wrong_species_forms_and_targets_are_not_selected(source, target):
    """The item cannot skip a stage or create/change Bloodmoon form."""
    assert get_evolution(source, level=100, item="Peat Block", target=target) is None


@pytest.mark.parametrize("field,value", [
    ("evoType", "newType"), ("evoCondition", "arbitrary full moon"),
    ("evoItem", "Peat Block"), ("prevo", "Teddiursa"),
    ("forme", "Bloodmoon"), ("baseSpecies", "Ursaluna"),
])
def test_changed_target_metadata_requires_a_new_review(monkeypatch, field, value):
    """The explicit exception does not authorize unknown/changed dex rules."""
    monkeypatch.setitem(lookup_species("Ursaluna").raw, field, value)
    assert get_evolution("Ursaring", level=100, item="Peat Block") is None


@pytest.mark.parametrize("source,target", [
    ("Inkay", "Malamar"), ("Primeape", "Annihilape"), ("Bisharp", "Kingambit"),
    ("Kubfu", "Urshifu"), ("Stantler", "Wyrdeer"), ("Milcery", "Alcremie"),
])
def test_unrelated_unsupported_rules_do_not_accept_peat_block(source, target):
    """A supplied bag item still cannot be spent on a different evolution."""
    assert get_evolution(source, level=100, item="Peat Block", target=target) is None


@pytest.mark.parametrize("source_ability,target_ability", [
    ("Guts", "Guts"), ("Quick Feet", "Bulletproof"), ("Unnerve", "Unnerve"),
])
def test_existing_transition_maps_ability_slot_without_consuming_held_item(source_ability, target_ability):
    """Application preserves unrelated held/name fields; service owns bag debit."""
    mon = SimpleNamespace(species="Ursaring", name="Buddy", nickname="Buddy", level=1,
                          ability=source_ability, held_item="Leftovers", type_="Normal")
    assert attempt_evolution(mon, item="Peat Block") == "Ursaluna"
    assert mon.ability == target_ability and mon.type_ == "Ground, Normal"
    assert mon.name == mon.nickname == "Buddy" and mon.held_item == "Leftovers"

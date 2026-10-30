"""Bounded rule/appearance contracts; production-model commands run separately."""

from types import SimpleNamespace

import pytest

from pokemon.data.evolution import EvolutionContext, attempt_evolution, get_evolution, lookup_species
from pokemon.evolution_forms import AlcremieEvolution
from pokemon.names import resolve_dex_entry


@pytest.mark.parametrize("sweet", AlcremieEvolution.sweets)
def test_existing_sweet_enables_only_the_explicit_milcery_transition(sweet):
    from pokemon.dex import ITEMDEX

    assert resolve_dex_entry(ITEMDEX, sweet) is not None
    context = EvolutionContext(held_item=sweet, gender="F")
    assert get_evolution("Milcery", level=1, context=context) == "Alcremie"
    assert get_evolution("Milcery", level=100, item=sweet, context=context) is None
    assert get_evolution("Inkay", level=100, context=context) is None


@pytest.mark.parametrize("item", ["", "Sweet", "Berry", "Sweet Apple", "Oran Berry", "Everstone"])
def test_missing_or_wrong_held_items_do_not_unlock_alcremie(item):
    assert get_evolution("Milcery", level=100, context=EvolutionContext(held_item=item, gender="F")) is None


def test_only_dex_declared_cosmetics_can_be_selected_and_displayed():
    base = lookup_species("Alcremie")
    assert AlcremieEvolution.forms() == ("Alcremie", *base.raw["cosmeticFormes"])
    assert len(AlcremieEvolution.forms()) == 9
    assert AlcremieEvolution.select("alcremie ruby cream") == "Alcremie-Ruby-Cream"
    assert AlcremieEvolution.select("Alcremie-Gmax") is None
    assert AlcremieEvolution.select("Alcremie-Chocolate-Cream") is None
    pokemon = SimpleNamespace(species="Alcremie", flags=["preserved"])
    AlcremieEvolution.decorate(pokemon, "Alcremie-Ruby-Cream", "Berry Sweet")
    assert "preserved" in pokemon.flags
    assert all(len(tag) <= 50 for tag in pokemon.flags)
    assert AlcremieEvolution.describe(pokemon) == "Ruby Cream; Berry Sweet"
    pokemon.species = "Pikachu"
    assert AlcremieEvolution.describe(pokemon) is None


@pytest.mark.parametrize("ability", ["Sweet Veil", "Aroma Veil"])
def test_native_transition_keeps_ability_slot_and_consumes_the_actual_held_sweet(ability):
    pokemon = SimpleNamespace(species="Milcery", name="Cream", nickname="Cream", level=1,
                              gender="F", ability=ability, held_item="Ribbon Sweet")
    assert attempt_evolution(pokemon) == "Alcremie"
    assert pokemon.ability == ability
    assert pokemon.held_item == ""
    assert pokemon.name == pokemon.nickname == "Cream"


def test_unknown_special_conditions_remain_closed_even_with_a_sweet(monkeypatch):
    target = lookup_species("Alcremie")
    monkeypatch.setitem(target.raw, "evoCondition", "unimplemented special action")
    assert get_evolution("Milcery", level=100, context=EvolutionContext(held_item="Star Sweet", gender="F")) is None


@pytest.mark.parametrize("tags", [
    ["alcremie:form:Alcremie-Gmax", "alcremie:sweet:Berry Sweet"],
    ["alcremie:form:Alcremie"],
    ["alcremie:form:Alcremie", "alcremie:sweet:Sweet Apple"],
    ["alcremie:form:Alcremie", "alcremie:form:Alcremie-Ruby-Cream", "alcremie:sweet:Berry Sweet"],
])
def test_incomplete_unknown_and_ambiguous_cosmetics_are_not_advertised(tags):
    pokemon = SimpleNamespace(species="Alcremie", flags=tags)
    assert AlcremieEvolution.describe(pokemon) is None

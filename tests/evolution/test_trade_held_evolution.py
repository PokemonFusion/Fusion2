"""Bounded trade-held rule coverage; real commands and SQL run separately."""

from types import SimpleNamespace

import pytest

from pokemon.data.evolution import EvolutionContext, attempt_evolution, get_evolution, lookup_species
from pokemon.dex import ITEMDEX, POKEDEX
from pokemon.evolution_items import TradeHeldEvolution
from pokemon.names import resolve_dex_entry


@pytest.mark.parametrize("source,target,item", TradeHeldEvolution.transitions)
def test_existing_item_maps_only_to_its_eligible_held_transition(source, target, item):
    """All listed items exist and use the held copy, never a bag argument."""
    assert resolve_dex_entry(ITEMDEX, item) is not None
    context = EvolutionContext(held_item=item)
    assert get_evolution(source, level=1, context=context) == target
    assert get_evolution(source, level=100, context=EvolutionContext(), target=target) is None
    assert get_evolution(source, level=100, item=item, context=context, target=target) is None
    assert get_evolution(source, level=100, context=EvolutionContext(held_item="Everstone"), target=target) is None
    pokemon = SimpleNamespace(species=source, name="Buddy", nickname="Buddy", level=1,
                              ability=lookup_species(source).raw["abilities"]["0"], held_item=item)
    assert attempt_evolution(pokemon) == target
    assert pokemon.held_item == ""
    assert pokemon.nickname == pokemon.name == "Buddy"


def test_reviewed_allowlist_covers_current_dex_without_enabling_other_trades():
    """A new trade definition requires review rather than implicit eligibility."""
    actual = {(p.raw["prevo"], p.name, p.raw["evoItem"]) for p in POKEDEX.values()
              if p.raw.get("evoType") == "trade" and p.raw.get("evoItem")}
    assert set(TradeHeldEvolution.transitions) == actual
    assert len(actual) == 17
    assert len({item for _, _, item in actual}) == 14
    for pokemon in POKEDEX.values():
        if pokemon.raw.get("evoType") == "trade" and not pokemon.raw.get("evoItem"):
            for item in ("", "Metal Coat", "King's Rock"):
                assert get_evolution(pokemon.raw["prevo"], level=100,
                                     context=EvolutionContext(held_item=item), target=pokemon.name) is None


@pytest.mark.parametrize("field,value", [
    ("evoItem", "Leftovers"), ("evoType", "newType"),
    ("evoCondition", "unimplemented ritual"), ("prevo", "Pikachu"),
])
def test_changed_metadata_cannot_enable_unknown_trade_rules(monkeypatch, field, value):
    """Allowlist entries cannot override the ordinary fail-closed evaluator."""
    monkeypatch.setitem(lookup_species("Scizor").raw, field, value)
    assert get_evolution("Scyther", level=100, context=EvolutionContext(held_item="Metal Coat")) is None


def test_wrong_species_branch_item_and_partial_target_fail_closed():
    """Shared held items never authorize foreign or regional holders."""
    for species in ("Pikachu", "Slowpoke-Galar", "Kadabra"):
        assert get_evolution(species, level=1, context=EvolutionContext(held_item="King's Rock"), target="Slowking") is None
    assert get_evolution("Clamperl", level=100, context=EvolutionContext(held_item="Deep Sea Scale"), target="Huntail") is None
    assert get_evolution("Scyther", level=100, context=EvolutionContext(held_item="Metal")) is None
    assert get_evolution("Scyther", level=100, context=EvolutionContext(held_item="metal-coat"), target="scizor") == "Scizor"

"""The manual coin equivalent admits only the reviewed native Chest transition."""

from types import SimpleNamespace

import pytest

from pokemon.data.evolution import EvolutionContext, attempt_evolution, evolution_options, lookup_species
from pokemon.items import get_gameplay_item


@pytest.mark.parametrize("level", [2, 50, 100])
def test_exact_coin_rule_and_native_ability_transition(level):
    """The explicit PF2 route preserves held ownership and native saved level."""
    mon = SimpleNamespace(species="Gimmighoul", level=level, ability="Rattled", held_item="Leftovers")
    assert attempt_evolution(mon, item="Gimmighoul Coin") == "Gholdengo"
    assert (mon.species, mon.ability, mon.held_item, mon.level) == ("Gholdengo", "Good as Gold", "Leftovers", level)


@pytest.mark.parametrize("source,item,level,ability", [
    ("Gimmighoul", None, 50, "Rattled"), ("Gimmighoul", "Coin", 50, "Rattled"),
    ("Gimmighoul", "Gimmighoul Coin", 1, "Rattled"), ("Gimmighoul", "Gimmighoul Coin", 101, "Rattled"),
    ("Gimmighoul", "Gimmighoul Coin", 50, "Run Away"),
    ("Gimmighoul-Roaming", "Gimmighoul Coin", 50, "Run Away"),
    ("Ditto", "Gimmighoul Coin", 50, "Rattled"), ("Gholdengo", "Gimmighoul Coin", 100, "Good as Gold"),
])
def test_missing_wrong_native_form_item_level_or_ability_cannot_qualify(source, item, level, ability):
    """Neither evolved/form metadata nor a nickname-like species guess is eligibility."""
    assert not evolution_options(source, level=level, item=item, context=EvolutionContext(ability=ability))


def test_everstone_and_target_metadata_remain_fail_closed(monkeypatch):
    """The coin equivalent never turns arbitrary dex prose into a predicate."""
    context = EvolutionContext(ability="Rattled", held_item="Everstone")
    assert not evolution_options("Gimmighoul", level=50, item="Gimmighoul Coin", context=context)
    monkeypatch.setitem(lookup_species("Gholdengo").raw, "evoCondition", "some coins and a flag")
    assert not evolution_options("Gimmighoul", level=50, item="Gimmighoul Coin", context=EvolutionContext(ability="Rattled"))


def test_coin_definition_is_exact_and_explains_quantity_and_form():
    """Metadata describes the rule but cannot by itself execute it."""
    item = get_gameplay_item("GIMMIGHOUL-COIN")
    assert item.name == "Gimmighoul Coin" and item.price == 10
    assert item.raw["category"] == "Evolution Items"
    assert "999" in item.desc and "Chest" in item.desc
    assert get_gameplay_item("Gimmighoul") is None

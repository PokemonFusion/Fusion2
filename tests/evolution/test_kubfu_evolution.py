"""Exact Kubfu Scroll mappings, complete item metadata and fail-closed rules."""

from types import SimpleNamespace

import pytest

from pokemon.data.evolution import (
    EvolutionContext, attempt_evolution, get_evolution, get_evolution_items, lookup_species,
)
from pokemon.items import get_gameplay_item, is_capture_ball
from pokemon.middleware import get_item_by_name

BRANCHES = (("Scroll of Darkness", "Urshifu"), ("Scroll of Waters", "Urshifu-Rapid-Strike"))


@pytest.mark.parametrize("item,target", BRANCHES)
@pytest.mark.parametrize("spelling", ["full", "upper", "hyphens"])
def test_complete_item_metadata_and_lookup(item, target, spelling):
    """Full names resolve consistently across item and evolution interfaces."""
    query = item.upper() if spelling == "upper" else item.replace(" ", "-") if spelling == "hyphens" else item
    definition = get_gameplay_item(query)
    assert definition.name == item and definition.category == "Evolution Items"
    assert definition.price == 10000 and definition.raw["category"] == "Evolution Items"
    assert target in definition.desc and "+evolve" in definition.desc and "one bag copy" in definition.desc
    assert get_item_by_name(query)[1] is definition
    assert item in get_evolution_items() and not is_capture_ball(query)


@pytest.mark.parametrize("query", ["Scroll", "Darkness", "Waters", "Scroll of", "Scroll of Water"])
def test_partial_item_names_are_not_accepted(query):
    """No partial/default Scroll identity grants a branch."""
    assert get_gameplay_item(query) is None
    assert get_evolution("Kubfu", level=100, item=query) is None


@pytest.mark.parametrize("item,target", BRANCHES)
@pytest.mark.parametrize("level", [1, 30, 100])
def test_bag_item_selects_exact_branch_without_extra_level_or_context(item, target, level):
    """Both paths work with absent time/region/friendship or tower context."""
    assert get_evolution("Kubfu", level=level, item=item) == target
    assert get_evolution("Kubfu", level=level, item=item, target=target) == target


@pytest.mark.parametrize("item,target", BRANCHES)
def test_missing_item_and_held_only_copies_do_not_activate(item, target):
    """Tower text, target and held state never replace the explicit bag input."""
    assert get_evolution("Kubfu", level=100, target=target) is None
    assert get_evolution("Kubfu", level=100, context=EvolutionContext(held_item=item, friendship=255)) is None
    assert not EvolutionContext().meets(lookup_species(target).raw["evoCondition"])


@pytest.mark.parametrize("item,target", BRANCHES)
def test_everstone_still_blocks(item, target):
    """A bounded rule exception does not skip the shared held-item guard."""
    assert get_evolution("Kubfu", level=100, item=item, context=EvolutionContext(held_item="Everstone")) is None


@pytest.mark.parametrize("item,target", BRANCHES)
def test_other_branch_and_gmax_targets_fail(item, target):
    """One Scroll cannot select an unrelated style or battle-only form."""
    wrong = "Urshifu-Rapid-Strike" if target == "Urshifu" else "Urshifu"
    for requested in (wrong, "Urshifu-Single-Strike", "Urshifu-Rapid", "Urshifu-Gmax", "Urshifu-Rapid-Strike-Gmax"):
        assert get_evolution("Kubfu", level=100, item=item, target=requested) is None


@pytest.mark.parametrize("item,target", BRANCHES)
@pytest.mark.parametrize("source", ["Pikachu", "Urshifu", "Urshifu-Rapid-Strike", "Urshifu-Gmax"])
def test_wrong_source_and_style_switches_are_not_supported(item, target, source):
    """Evolved or unrelated species cannot use the source-specific mapping."""
    assert get_evolution(source, level=100, item=item, target=target) is None


@pytest.mark.parametrize("item,target", BRANCHES)
@pytest.mark.parametrize("field,value", [("evoType", "future"), ("evoCondition", "unreviewed tower"),
                                        ("evoItem", "Scroll"), ("prevo", "Pikachu"),
                                        ("forme", "Foreign"), ("baseSpecies", "Foreign"),
                                        ("baseForme", "Foreign"), ("battleOnly", "Kubfu"),
                                        ("changesFrom", "Kubfu")])
def test_unreviewed_target_metadata_fails_closed(monkeypatch, item, target, field, value):
    """Do not let future form or predicate changes inherit this exception."""
    monkeypatch.setitem(lookup_species(target).raw, field, value)
    assert get_evolution("Kubfu", level=100, item=item) is None


@pytest.mark.parametrize("field,value", [("forme", "Foreign"), ("baseSpecies", "Kubfu"),
                                        ("baseForme", "Foreign"), ("evos", [])])
def test_native_source_metadata_and_successor_list_remain_required(monkeypatch, field, value):
    """Nicknames and foreign form metadata cannot supply native identity."""
    source = lookup_species("Kubfu")
    if field == "evos":
        monkeypatch.setattr(source, "evos", value)
    else:
        monkeypatch.setitem(source.raw, field, value)
    for item, _ in BRANCHES:
        assert get_evolution("Kubfu", level=100, item=item) is None


@pytest.mark.parametrize("item,target", BRANCHES)
def test_shared_level_gender_and_region_checks_are_retained(monkeypatch, item, target):
    """Only the reviewed tower predicate is replaced, not other dex limits."""
    data = lookup_species(target)
    monkeypatch.setattr(data, "evo_level", 30)
    assert get_evolution("Kubfu", level=29, item=item) is None
    monkeypatch.setitem(data.raw, "gender", "F")
    assert get_evolution("Kubfu", level=30, item=item, context=EvolutionContext(gender="M")) is None
    monkeypatch.setitem(data.raw, "evoRegion", "Galar")
    assert get_evolution("Kubfu", level=30, item=item, context=EvolutionContext(gender="F")) is None
    assert get_evolution("Kubfu", level=30, item=item,
                         context=EvolutionContext(gender="F", region="Galar")) == target


@pytest.mark.parametrize("item,target", BRANCHES)
def test_transition_maps_ability_and_preserves_held_item_and_nickname(item, target):
    """The shared in-memory transition preserves the actual holder's state."""
    mon = SimpleNamespace(species="Kubfu", name="Buddy", nickname="Buddy", level=1,
                          ability="Inner Focus", held_item=item, type_="Fighting")
    assert attempt_evolution(mon, item=item) == target
    assert mon.species == target and mon.ability == "Unseen Fist"
    assert mon.held_item == item and mon.nickname == mon.name == "Buddy"


@pytest.mark.parametrize("source", ["Inkay", "Primeape", "Bisharp", "Ursaring"])
def test_scrolls_do_not_unlock_unrelated_other_rules(source):
    """No generic other-condition override or stone fallback is added."""
    assert get_evolution(source, level=100, item="Scroll of Waters") is None

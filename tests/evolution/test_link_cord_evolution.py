"""Exact bag-cord transitions, native forms and unchanged held-item routes."""

from types import SimpleNamespace

import pytest

from pokemon.data.evolution import (
    EvolutionContext, attempt_evolution, get_evolution, get_evolution_items, lookup_species,
)
from pokemon.dex import POKEDEX
from pokemon.evolution_items import LinkCordEvolution, TradeHeldEvolution
from pokemon.items import get_gameplay_item, is_capture_ball
from pokemon.middleware import get_item_by_name


def test_allowlist_covers_all_canonical_trade_only_dex_transitions():
    """All regional/size mappings are included, while fan species stay excluded."""
    actual = {(entry.raw["prevo"], entry.name) for entry in POKEDEX.values()
              if entry.num > 0 and entry.raw.get("evoType") == "trade"
              and not entry.raw.get("evoItem")}
    assert set(LinkCordEvolution.transitions) == actual
    assert len(actual) == 14
    assert get_evolution("Tactite", level=100, item="Link Cord") is None


@pytest.mark.parametrize("query", ["Link Cord", "LINK CORD", "link-cord", "linkcord"])
def test_complete_item_lookup_and_player_metadata(query):
    """Inventory, itemdex and evolution discovery share one complete identity."""
    item = get_gameplay_item(query)
    assert item.name == "Link Cord" and item.category == "Evolution Items"
    assert "one bag copy" in item.desc and "+evolve <id> Link Cord" in item.desc
    assert get_item_by_name(query)[1] is item
    assert "Link Cord" in get_evolution_items()
    assert not is_capture_ball(query)


@pytest.mark.parametrize("source,target", LinkCordEvolution.transitions)
@pytest.mark.parametrize("level", [1, 30, 100])
def test_bag_cord_selects_only_exact_successor_without_partner_or_room(source, target, level):
    """No room region or partner Pokemon is needed, even for the paired bugs."""
    assert get_evolution(source, level=level, item="Link Cord") == target
    assert get_evolution(source, level=level, item="link-cord", target=target.lower()) == target
    for other in {name for _, name in LinkCordEvolution.transitions} - {target}:
        assert get_evolution(source, level=level, item="Link Cord", target=other) is None


@pytest.mark.parametrize("source,target", LinkCordEvolution.transitions)
def test_explicit_bag_input_and_everstone_guard(source, target):
    """Held-only copies and a requested target do not replace the bag action."""
    assert get_evolution(source, level=100, target=target) is None
    assert get_evolution(source, level=100, context=EvolutionContext(held_item="Link Cord")) is None
    assert get_evolution(source, level=100, item="Link Cord",
                         context=EvolutionContext(held_item="Everstone")) is None


@pytest.mark.parametrize("item", ["Link", "Cord", "Linking Cord", "Metal Coat", "Fire Stone"])
def test_partial_and_wrong_items_do_not_activate(item):
    """A nickname-like item name cannot grant a trade-only transition."""
    assert get_evolution("Haunter", level=100, item=item) is None
    if item in {"Link", "Cord", "Linking Cord"}:
        assert get_gameplay_item(item) is None


@pytest.mark.parametrize("level", [-1, 0, 101, True, 30.5, "30", None])
def test_invalid_saved_level_fails_closed(level):
    """The new route accepts only legal stored integer levels."""
    assert get_evolution("Haunter", level=level, item="Link Cord") is None


@pytest.mark.parametrize("source,target", LinkCordEvolution.transitions)
def test_native_ability_slots_types_and_unrelated_held_state_are_preserved(source, target):
    """The shared transition changes species/types/ability while retaining other state."""
    abilities = lookup_species(source).raw["abilities"]
    for slot, ability in abilities.items():
        mon = SimpleNamespace(species=source, name="Buddy", nickname="Buddy", level=30,
                              ability=ability, held_item="Link Cord", type_="old",
                              current_hp=3, status="slp", total_exp=12345)
        assert attempt_evolution(mon, item="Link Cord") == target
        target_data = lookup_species(target)
        assert mon.ability == target_data.raw["abilities"].get(slot, target_data.raw["abilities"]["0"])
        assert mon.type_ == ", ".join(target_data.types)
        assert (mon.held_item, mon.name, mon.nickname, mon.current_hp, mon.status, mon.total_exp) == (
            "Link Cord", "Buddy", "Buddy", 3, "slp", 12345,
        )


@pytest.mark.parametrize("source,target,item", TradeHeldEvolution.transitions)
def test_existing_trade_held_routes_do_not_require_or_accept_cord(source, target, item):
    """All 17 held-item equivalents retain their original item/consumption policy."""
    context = EvolutionContext(held_item=item)
    assert get_evolution(source, level=30, context=context) == target
    assert get_evolution(source, level=30, item="Link Cord", context=context) is None
    assert get_evolution(source, level=30, item="Link Cord") is None


@pytest.mark.parametrize("source,target", LinkCordEvolution.transitions)
@pytest.mark.parametrize("field,value", [
    ("evoType", "future"), ("evoType", "useItem"), ("evoItem", "Link Cord"),
    ("evoCondition", "unreviewed ritual"), ("prevo", "Ditto"),
    ("forme", "Foreign"), ("baseSpecies", "Foreign"), ("baseForme", "Foreign"),
    ("battleOnly", "Haunter"), ("changesFrom", "Haunter"),
])
def test_changed_target_metadata_requires_review(monkeypatch, source, target, field, value):
    """The bag rule never grants arbitrary new kinds, forms or conditions."""
    monkeypatch.setitem(lookup_species(target).raw, field, value)
    assert get_evolution(source, level=100, item="Link Cord") is None


@pytest.mark.parametrize("source,target", LinkCordEvolution.transitions)
@pytest.mark.parametrize("field,value", [
    ("forme", "Foreign"), ("baseSpecies", "Foreign"), ("baseForme", "Foreign"),
    ("battleOnly", "Ditto"), ("changesFrom", "Ditto"),
])
def test_changed_native_source_metadata_requires_review(monkeypatch, source, target, field, value):
    """Exact source species alone cannot bypass foreign form metadata."""
    monkeypatch.setitem(lookup_species(source).raw, field, value)
    assert get_evolution(source, level=100, item="Link Cord") is None


def test_source_successor_and_shared_level_gender_region_checks_still_apply(monkeypatch):
    """Only the trade predicate is replaced; ordinary dex guards remain shared."""
    source, target = lookup_species("Haunter"), lookup_species("Gengar")
    monkeypatch.setattr(source, "evos", [])
    assert get_evolution(source.name, level=30, item="Link Cord") is None
    monkeypatch.setattr(source, "evos", [target.name])
    monkeypatch.setattr(target, "evo_level", 30)
    assert get_evolution(source.name, level=29, item="Link Cord") is None
    monkeypatch.setitem(target.raw, "gender", "F")
    assert get_evolution(source.name, level=30, item="Link Cord") is None
    monkeypatch.setitem(target.raw, "evoRegion", "Kanto")
    assert get_evolution(source.name, level=30, item="Link Cord", context=EvolutionContext(gender="F")) is None
    assert get_evolution(source.name, level=30, item="Link Cord",
                         context=EvolutionContext(gender="F", region="Kanto")) == "Gengar"


@pytest.mark.parametrize("source", ["Gastly", "Geodude-Alola", "Gengar", "Pikachu", "Ditto", "Inkay"])
def test_other_species_and_completed_evolutions_do_not_accept_cord(source):
    """A cord cannot skip stages, transform a foreign holder or trigger other rules."""
    assert get_evolution(source, level=100, item="Link Cord") is None

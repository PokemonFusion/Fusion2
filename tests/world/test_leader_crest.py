"""Bounded Kingambit rule, item metadata and structured qualification limits."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from pokemon.data.evolution import EvolutionContext, attempt_evolution, get_evolution, lookup_species
from pokemon.items import get_gameplay_item, is_capture_ball
from pokemon.middleware import get_item_by_name
from pokemon.services.leader_crest import LeaderQualification


@pytest.mark.parametrize("query", ["Leader's Crest", "Leader’s Crest", "LEADERSCREST", "leaders-crest"])
def test_complete_definition_and_non_capture_qualification_role(query):
    """Crest lookup/display is complete and has no disposable bag-use effect."""
    item = get_gameplay_item(query)
    assert get_item_by_name(query)[1] is item
    assert item.name == "Leader's Crest" and item.category == "Held Items"
    assert item.raw["qualificationOnly"] and item.price == 1500
    assert "+evolve" in item.desc and "required or consumed" in item.desc
    assert not is_capture_ball(query)


@pytest.mark.parametrize("query", ["Leader", "Crest", "Leaders", "Kingambit Crest"])
def test_partial_item_identity_is_not_accepted(query):
    """This addition does not broaden complete-name lookup."""
    assert get_gameplay_item(query) is None


@pytest.mark.parametrize("count,level,expected", [(0, 53, False), (1, 53, False), (2, 53, False),
                                                (3, 52, False), (3, 53, True), (3, 100, True)])
def test_threshold_requires_three_distinct_leaders_and_a_level_increase(count, level, expected):
    """The pure rule consumes readiness, never an arbitrary count/flag input."""
    progress = LeaderQualification(tuple(str(uuid4()) for _ in range(count)), 52)
    ready = progress.ready(level)
    assert ready is expected
    assert get_evolution("Bisharp", level=level, context=EvolutionContext(kingambit_ready=ready)) == (
        "Kingambit" if expected else None
    )


@pytest.mark.parametrize("ability,expected", [("Defiant", "Defiant"), ("Inner Focus", "Supreme Overlord"),
                                             ("Pressure", "Pressure")])
def test_transition_retains_native_ability_slot_and_all_held_items(ability, expected):
    """The player's Crest is neither required nor consumed by evolution."""
    mon = SimpleNamespace(species="Bisharp", name="Buddy", nickname="Buddy", level=53,
                          ability=ability, held_item="Leader's Crest", type_="Dark, Steel")
    assert attempt_evolution(mon, context=EvolutionContext(kingambit_ready=True)) == "Kingambit"
    assert mon.ability == expected and mon.name == mon.nickname == "Buddy"
    assert mon.held_item == "Leader's Crest"


@pytest.mark.parametrize("item", ["Leader's Crest", "Peat Block", "Metal Coat"])
def test_no_bag_item_is_a_kingambit_stone_even_when_qualified(item):
    """Bag arguments still reject unrelated non-item evolutions."""
    assert get_evolution("Bisharp", level=100, item=item, context=EvolutionContext(kingambit_ready=True)) is None


@pytest.mark.parametrize("held", ["", "Leader's Crest", "Leftovers", "Everstone"])
def test_held_item_and_missing_evidence_cannot_manufacture_progress(held):
    """Holding a Crest does not supply private server readiness."""
    assert get_evolution("Bisharp", level=100, context=EvolutionContext(held_item=held)) is None
    if held == "Everstone":
        assert get_evolution("Bisharp", level=100,
                             context=EvolutionContext(held_item=held, kingambit_ready=True)) is None


@pytest.mark.parametrize("field,value", [("evoType", "newType"), ("evoCondition", "unknown ritual"),
                                        ("prevo", "Pawniard"), ("forme", "Foreign"),
                                        ("baseSpecies", "Kingambit"), ("evoItem", "Leader's Crest")])
def test_changed_metadata_fails_closed_even_with_real_readiness(monkeypatch, field, value):
    """The exception stays limited to the reviewed native transition."""
    monkeypatch.setitem(lookup_species("Kingambit").raw, field, value)
    assert get_evolution("Bisharp", level=100, context=EvolutionContext(kingambit_ready=True)) is None


def test_private_evidence_parse_binds_owner_identity_and_well_formed_unique_leaders():
    """Reject malformed/cross-owner/count-only records rather than trusting flags."""
    own = str(uuid4())
    data = {"version": 1, "trainer": 7, "pokemon": own,
            "leaders": [str(uuid4()) for _ in range(3)], "level_floor": 52}
    assert LeaderQualification.parse(data, own, 7).ready(53)
    assert LeaderQualification.parse(data, own, 8) is None
    assert LeaderQualification.parse(data, uuid4(), 7) is None
    for changes in ({"version": 2}, {"level_floor": True}, {"level_floor": -1},
                    {"leaders": ["fake"]}, {"leaders": [data["leaders"][0]] * 3},
                    {"leaders": []}, {"leaders": data["leaders"] + [str(uuid4())]}):
        assert LeaderQualification.parse({**data, **changes}, own, 7) is None
    assert LeaderQualification.parse({"count": 3, "ready": True}, own, 7) is None
    assert not LeaderQualification(tuple(data["leaders"]), 100).ready(100)


@pytest.mark.parametrize("source,target", [("Pawniard", "Kingambit"), ("Inkay", "Malamar"),
                                          ("Primeape", "Annihilape"), ("Kubfu", "Urshifu")])
def test_ready_kingambit_evidence_does_not_unlock_other_sources_or_rules(source, target):
    """Private progress is not a generic other-condition override."""
    assert get_evolution(source, level=100, target=target, context=EvolutionContext(kingambit_ready=True)) is None

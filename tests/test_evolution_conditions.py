"""Real dex coverage: each supported predicate fails closed without evidence."""

import pytest

from pokemon.data.evolution import (
    SUPPORTED_CONDITIONS,
    SUPPORTED_TYPES,
    UNSUPPORTED_CONDITIONS,
    UNSUPPORTED_TYPES,
    EvolutionContext,
    get_evolution,
    lookup_species,
)
from pokemon.dex import POKEDEX


@pytest.mark.parametrize(
    "source,target,level,item,context",
    [
        ("Bulbasaur", "Ivysaur", 16, None, EvolutionContext()),
        ("Vulpix", "Ninetales", 1, "Fire Stone", EvolutionContext()),
        ("Golbat", "Crobat", 2, None, EvolutionContext(friendship=160)),
        ("Tangela", "Tangrowth", 2, None, EvolutionContext(moves=("Ancient Power",))),
        ("Gligar", "Gliscor", 2, None, EvolutionContext(held_item="Razor Fang", time="night")),
        ("Happiny", "Chansey", 2, None, EvolutionContext(held_item="Oval Stone", time="day", gender="F")),
        ("Eevee", "Sylveon", 2, None, EvolutionContext(friendship=160, move_types=("Fairy",), time="day")),
        ("Eevee", "Espeon", 2, None, EvolutionContext(friendship=160, time="day")),
        ("Mantyke", "Mantine", 2, None, EvolutionContext(party_species=("Remoraid",))),
        ("Nosepass", "Probopass", 2, None, EvolutionContext(magnetic_field=True)),
        ("Pancham", "Pangoro", 32, None, EvolutionContext(party_types=("Dark",))),
        ("Sliggoo", "Goodra", 50, None, EvolutionContext(weather="rain")),
        ("Tyrogue", "Hitmonlee", 20, None, EvolutionContext(stats={"atk": 30, "def": 20}, gender="M")),
        ("Tyrogue", "Hitmonchan", 20, None, EvolutionContext(stats={"atk": 10, "def": 20}, gender="M")),
        ("Tyrogue", "Hitmontop", 20, None, EvolutionContext(stats={"atk": 20, "def": 20}, gender="M")),
        ("Pikachu", "Raichu-Alola", 2, "Thunder Stone", EvolutionContext(region="Alola")),
        ("Mime Jr.", "Mr. Mime-Galar", 2, None, EvolutionContext(region="Galar", moves=("Mimic",))),
        ("Kirlia", "Gallade", 20, "Dawn Stone", EvolutionContext(gender="M")),
        ("Rockruff", "Lycanroc-Dusk", 25, None, EvolutionContext(ability="Own Tempo", time="dusk")),
        ("Scyther", "Kleavor", 1, "Black Augurite", EvolutionContext()),
        ("Toxel", "Toxtricity-Low-Key", 30, None, EvolutionContext(nature="Modest")),
        ("Poltchageist-Artisan", "Sinistcha-Masterpiece", 1, "Masterpiece Teacup", EvolutionContext()),
    ],
)
def test_supported_real_data(source, target, level, item, context):
    assert get_evolution(source, level=level, item=item, context=context) == target
    if lookup_species(target).evo_level:
        assert get_evolution(source, level=level - 1, item=item, context=context, target=target) is None


@pytest.mark.parametrize(
    "source,item,context",
    [
        ("Golbat", None, EvolutionContext(friendship=159)),
        ("Tangela", None, EvolutionContext(moves=("Ancient",))),
        ("Gligar", None, EvolutionContext(held_item="Razor Fang", time="day")),
        ("Gligar", "Razor Fang", EvolutionContext(time="night")),
        ("Happiny", None, EvolutionContext(time="day", gender="F")),
        ("Eevee", None, EvolutionContext(friendship=160)),
        ("Nosepass", None, EvolutionContext()),
        ("Mantyke", None, EvolutionContext()),
        ("Pancham", None, EvolutionContext()),
        ("Sliggoo", None, EvolutionContext(weather="clear")),
        ("Kirlia", "Dawn Stone", EvolutionContext(gender="F")),
        ("Vulpix", "Fire", EvolutionContext()),
        ("Bulbasaur", "Fire Stone", EvolutionContext()),
        ("Bulbasaur", None, EvolutionContext(held_item="Everstone")),
        ("Kadabra", None, EvolutionContext()),
        ("Scyther", "Metal Coat", EvolutionContext()),
        ("Primeape", None, EvolutionContext()),
        ("Inkay", None, EvolutionContext()),
        ("Finizen", None, EvolutionContext()),
        ("Rockruff", None, EvolutionContext(ability="Own Tempo", time="day")),
        ("Poltchageist", "Masterpiece Teacup", EvolutionContext()),
    ],
)
def test_missing_or_unsupported_condition_never_becomes_generic_level(source, item, context):
    assert get_evolution(source, level=100, item=item, context=context) is None


def test_branch_selection_requires_exact_eligible_direct_successor():
    assert get_evolution("Gloom", level=50, item="Leaf Stone", target="Bellossom") is None
    assert get_evolution("Bulbasaur", level=100, target="Venusaur") is None
    assert get_evolution("Dunsparce", level=50, context=EvolutionContext(moves=("Hyper Drill",))) is None
    assert (
        get_evolution(
            "Dunsparce", level=50, context=EvolutionContext(moves=("Hyper Drill",)), target="Dudunsparce-Three-Segment"
        )
        == "Dudunsparce-Three-Segment"
    )


def test_all_positive_dex_links_resolve_and_condition_classes_are_enumerated():
    for source in POKEDEX.values():
        if source.num <= 0:
            continue
        for name in source.evos:
            target = lookup_species(name)
            assert target is not None, (source.name, name)
            kind = target.raw.get("evoType", "level")
            assert kind in SUPPORTED_TYPES | UNSUPPORTED_TYPES
            if kind not in UNSUPPORTED_TYPES and target.name != "Kleavor":
                assert target.raw.get("evoCondition", "") in SUPPORTED_CONDITIONS | UNSUPPORTED_CONDITIONS


def test_unknown_condition_and_type_fail_closed(monkeypatch):
    target = lookup_species("Ivysaur")
    monkeypatch.setitem(target.raw, "evoCondition", "new unimplemented requirement")
    assert get_evolution("Bulbasaur", level=100) is None
    monkeypatch.setitem(target.raw, "evoCondition", "")
    monkeypatch.setitem(target.raw, "evoType", "newType")
    assert get_evolution("Bulbasaur", level=100) is None


def test_regional_branch_cannot_bypass_time_by_selecting_base_form():
    for target in (None, "Marowak", "Marowak-Alola"):
        assert (
            get_evolution("Cubone", level=40, target=target, context=EvolutionContext(region="Alola", time="day"))
            is None
        )


def test_evolution_maps_ability_slot_and_preserves_nickname():
    from types import SimpleNamespace

    from pokemon.data.evolution import attempt_evolution

    pokemon = SimpleNamespace(
        species="Eevee", name="Buddy", nickname="Buddy", level=10, ability="Anticipation", held_item=""
    )
    assert attempt_evolution(pokemon, item="Water Stone") == "Vaporeon"
    assert pokemon.ability == "Hydration"
    assert pokemon.name == pokemon.nickname == "Buddy"

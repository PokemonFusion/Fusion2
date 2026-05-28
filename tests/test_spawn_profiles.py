import random
from dataclasses import fields

import pytest

from pokemon.spawns.profiles import (
    AreaSpawnEntry,
    AreaSpawnProfile,
    SpawnProfileError,
    SpeciesSpawnProfile,
    resolve_area_spawn_chart,
    validate_area_spawn_entry,
    validate_species_spawn_profile,
)
from pokemon.spawns.schema import SpawnEntry
from pokemon.spawns.selection import roll_spawn


def test_global_profile_alone_does_nothing_without_area_entry():
    chart = resolve_area_spawn_chart(
        AreaSpawnProfile(area_key="route-empty", entries=[]),
        [SpeciesSpawnProfile("Pidgey", {1: "common"})],
    )

    assert chart.area_key == "route-empty"
    assert chart.entries == []


def test_area_entry_plus_global_profile_resolves_entries():
    chart = resolve_area_spawn_chart(
        AreaSpawnProfile(area_key="route-alpha", entries=[AreaSpawnEntry("Pidgey")]),
        [SpeciesSpawnProfile("Pidgey", {1: "common", 2: "uncommon"})],
    )

    assert chart.entries == [
        SpawnEntry(species_id="Pidgey", frequency="common", band=1),
        SpawnEntry(species_id="Pidgey", frequency="uncommon", band=2),
    ]


def test_area_entry_without_override_uses_global_frequency():
    chart = resolve_area_spawn_chart(
        AreaSpawnProfile(area_key="route-alpha", entries=[AreaSpawnEntry("Pidgey")]),
        {"Pidgey": SpeciesSpawnProfile("Pidgey", {1: "rare"})},
    )

    assert chart.entries == [SpawnEntry(species_id="Pidgey", frequency="rare", band=1)]


def test_area_entry_override_changes_one_band_frequency():
    chart = resolve_area_spawn_chart(
        AreaSpawnProfile(
            area_key="route-alpha",
            entries=[AreaSpawnEntry("Pidgey", frequency_overrides_by_band={2: "frequent"})],
        ),
        [SpeciesSpawnProfile("Pidgey", {1: "common", 2: "rare"})],
    )

    assert chart.entries == [
        SpawnEntry(species_id="Pidgey", frequency="common", band=1),
        SpawnEntry(species_id="Pidgey", frequency="frequent", band=2),
    ]


def test_none_override_means_no_override_and_uses_global_frequency():
    chart = resolve_area_spawn_chart(
        AreaSpawnProfile(
            area_key="route-alpha",
            entries=[AreaSpawnEntry("Pidgey", frequency_overrides_by_band={1: None})],
        ),
        [SpeciesSpawnProfile("Pidgey", {1: "rare"})],
    )

    assert chart.entries == [SpawnEntry(species_id="Pidgey", frequency="rare", band=1)]


def test_area_entry_can_enable_form_species_ids():
    chart = resolve_area_spawn_chart(
        AreaSpawnProfile(
            area_key="forms",
            entries=[
                AreaSpawnEntry("479F"),
                AreaSpawnEntry("487+"),
                AreaSpawnEntry("678M"),
            ],
        ),
        [
            SpeciesSpawnProfile("479F", {1: "common"}),
            SpeciesSpawnProfile("487+", {2: "uncommon"}),
            SpeciesSpawnProfile("678M", {4: "rare"}),
        ],
    )

    assert [entry.species_id for entry in chart.entries] == ["479F", "487+", "678M"]


def test_disabled_species_profile_prevents_entries():
    chart = resolve_area_spawn_chart(
        AreaSpawnProfile(area_key="route-alpha", entries=[AreaSpawnEntry("Pidgey")]),
        [SpeciesSpawnProfile("Pidgey", {1: "common"}, enabled=False)],
    )

    assert chart.entries == []


def test_disabled_area_entry_prevents_entries():
    chart = resolve_area_spawn_chart(
        AreaSpawnProfile(area_key="route-alpha", entries=[AreaSpawnEntry("Pidgey", enabled=False)]),
        [SpeciesSpawnProfile("Pidgey", {1: "common"})],
    )

    assert chart.entries == []


def test_missing_global_profile_skips_species_without_override():
    chart = resolve_area_spawn_chart(
        AreaSpawnProfile(area_key="route-alpha", entries=[AreaSpawnEntry("Pidgey")]),
        [],
    )

    assert chart.entries == []


def test_missing_global_profile_allows_real_area_overrides():
    chart = resolve_area_spawn_chart(
        AreaSpawnProfile(
            area_key="route-alpha",
            entries=[AreaSpawnEntry("Pidgey", frequency_overrides_by_band={1: "common"})],
        ),
        [],
    )

    assert chart.entries == [SpawnEntry(species_id="Pidgey", frequency="common", band=1)]


def test_invalid_frequency_raises_clear_error():
    with pytest.raises(SpawnProfileError, match="Invalid spawn frequency"):
        validate_species_spawn_profile(SpeciesSpawnProfile("Pidgey", {1: "everywhere"}))
    with pytest.raises(SpawnProfileError, match="Invalid spawn frequency"):
        validate_area_spawn_entry(AreaSpawnEntry("Pidgey", frequency_overrides_by_band={1: "everywhere"}))


def test_invalid_band_raises_clear_error():
    with pytest.raises(SpawnProfileError, match="Invalid spawn band"):
        validate_species_spawn_profile(SpeciesSpawnProfile("Pidgey", {5: "common"}))
    with pytest.raises(SpawnProfileError, match="Invalid spawn band"):
        validate_area_spawn_entry(AreaSpawnEntry("Pidgey", frequency_overrides_by_band={0: "common"}))


def test_species_with_no_frequency_for_band_produces_no_entry_for_that_band():
    chart = resolve_area_spawn_chart(
        AreaSpawnProfile(area_key="route-alpha", entries=[AreaSpawnEntry("Pidgey")]),
        [SpeciesSpawnProfile("Pidgey", {1: "common", 2: None})],
    )

    assert chart.entries == [SpawnEntry(species_id="Pidgey", frequency="common", band=1)]


def test_resolved_spawn_chart_works_with_roll_spawn():
    chart = resolve_area_spawn_chart(
        AreaSpawnProfile(area_key="route-alpha", entries=[AreaSpawnEntry("Pidgey")]),
        [SpeciesSpawnProfile("Pidgey", {1: "common"})],
    )

    result = roll_spawn(chart, 1, rng=random.Random(1))

    assert result.species_id == "Pidgey"
    assert result.frequency == "common"
    assert result.band == 1
    assert 5 <= result.level <= 15


def test_no_version_or_variant_fields_exist_or_are_required():
    assert {field.name for field in fields(SpeciesSpawnProfile)} == {
        "species_id",
        "frequencies_by_band",
        "enabled",
    }
    assert {field.name for field in fields(AreaSpawnEntry)} == {
        "species_id",
        "enabled",
        "frequency_overrides_by_band",
    }
    assert {field.name for field in fields(AreaSpawnProfile)} == {"area_key", "entries"}
    with pytest.raises(TypeError):
        AreaSpawnEntry("Pidgey", version=1)
    with pytest.raises(TypeError):
        SpeciesSpawnProfile("Pidgey", {1: "common"}, variant="V2")

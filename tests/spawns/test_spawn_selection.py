import random
from dataclasses import fields

import pytest

from pokemon.spawns.constants import (
    ACTIVE_COUNTS,
    FREQUENCIES,
    FREQUENCY_WEIGHTS,
    NORMAL_FREQUENCIES,
    SPAWN_BANDS,
    SpawnFrequency,
)
from pokemon.spawns.schema import RotationBucket, SpawnChart, SpawnEntry, SpawnRollResult
from pokemon.spawns.selection import (
    build_rotation_buckets,
    eligible_entries,
    refresh_rotation_bucket,
    roll_frequency_for_band,
    roll_level_for_band,
    roll_spawn,
    validate_spawn_chart,
)


def test_band_constants_match_pf1_values():
    assert {
        band: (definition.access_value, definition.min_level, definition.max_level)
        for band, definition in SPAWN_BANDS.items()
    } == {
        1: (1, 5, 15),
        2: (15, 15, 30),
        3: (30, 30, 45),
        4: (45, 45, 60),
    }


def test_frequency_constants_match_pf2_list():
    assert FREQUENCIES == ("frequent", "common", "uncommon", "rare", "special")
    assert NORMAL_FREQUENCIES == ("frequent", "common", "uncommon", "rare")


def test_active_counts_match_pf1_rotation_counts():
    assert ACTIVE_COUNTS == {
        "frequent": 1,
        "common": 3,
        "uncommon": 2,
        "rare": 1,
        "special": 1,
    }


def test_special_has_zero_normal_roll_weight():
    assert all(weights["special"] == 0 for weights in FREQUENCY_WEIGHTS.values())


def test_spawn_entry_accepts_species_string_keys():
    entries = [
        SpawnEntry(species_id="025", frequency="frequent", band=1),
        SpawnEntry(species_id="479F", frequency="common", band=2),
        SpawnEntry(species_id="487+", frequency="uncommon", band=3),
        SpawnEntry(species_id="678M", frequency="rare", band=4),
    ]

    chart = SpawnChart(area_key="route-alpha", entries=entries)

    assert validate_spawn_chart(chart) is chart


def test_spawn_entry_has_no_version_or_variant_fields():
    field_names = {field.name for field in fields(SpawnEntry)}

    assert field_names == {"species_id", "frequency", "band", "enabled"}
    with pytest.raises(TypeError):
        SpawnEntry(species_id="025", frequency="frequent", band=1, version=1)
    with pytest.raises(TypeError):
        SpawnEntry(species_id="025", frequency="frequent", band=1, variant="V2")


@pytest.mark.parametrize(
    "chart, message",
    [
        (
            SpawnChart(area_key="", entries=[SpawnEntry(species_id="025", frequency="frequent", band=1)]),
            "area_key",
        ),
        (
            SpawnChart(area_key="route-alpha", entries=[SpawnEntry(species_id="025", frequency="missing", band=1)]),
            "frequency",
        ),
        (
            SpawnChart(area_key="route-alpha", entries=[SpawnEntry(species_id="025", frequency="frequent", band=9)]),
            "band",
        ),
    ],
)
def test_validate_spawn_chart_catches_invalid_data(chart, message):
    with pytest.raises(ValueError, match=message):
        validate_spawn_chart(chart)


def test_validate_spawn_chart_limits_special_entries_to_band_four():
    chart = SpawnChart(
        area_key="route-alpha",
        entries=[SpawnEntry(species_id="Legend", frequency="special", band=3)],
    )

    with pytest.raises(ValueError, match="Special"):
        validate_spawn_chart(chart)


def test_roll_level_for_band_stays_within_inclusive_range():
    rng = random.Random(7)

    for band, definition in SPAWN_BANDS.items():
        rolls = [roll_level_for_band(band, rng=rng) for _ in range(50)]
        assert all(definition.min_level <= level <= definition.max_level for level in rolls)


def test_roll_frequency_for_band_is_deterministic_with_seeded_random():
    first_rng = random.Random(12)
    second_rng = random.Random(12)

    assert [roll_frequency_for_band(2, first_rng) for _ in range(8)] == [
        roll_frequency_for_band(2, second_rng) for _ in range(8)
    ]


def test_eligible_entries_filters_by_band_frequency_and_enabled():
    chart = SpawnChart(
        area_key="route-alpha",
        entries=[
            SpawnEntry(species_id="A", frequency="frequent", band=1),
            SpawnEntry(species_id="B", frequency="common", band=1),
            SpawnEntry(species_id="C", frequency="common", band=2),
            SpawnEntry(species_id="D", frequency="common", band=1, enabled=False),
        ],
    )

    assert [entry.species_id for entry in eligible_entries(chart, 1)] == ["A", "B"]
    assert [entry.species_id for entry in eligible_entries(chart, 1, frequency="common")] == ["B"]


def test_refresh_rotation_bucket_moves_active_to_used():
    bucket = RotationBucket(queued=["B"], active=["A"], used=[])

    refreshed = refresh_rotation_bucket(bucket, ["A", "B"], active_count=1, rng=random.Random(1))

    assert refreshed.active == ["B"]
    assert refreshed.used == ["A"]


def test_refresh_rotation_bucket_chooses_from_queued_first():
    bucket = RotationBucket(queued=["B", "C"], active=[], used=["A"])

    refreshed = refresh_rotation_bucket(bucket, ["A", "B", "C"], active_count=2, rng=random.Random(4))

    assert set(refreshed.active) == {"B", "C"}
    assert refreshed.used == ["A"]


def test_refresh_rotation_bucket_recycles_used_when_queue_exhausted():
    bucket = RotationBucket(queued=[], active=[], used=["A", "B"])

    refreshed = refresh_rotation_bucket(bucket, ["A", "B"], active_count=1, rng=random.Random(2))

    assert len(refreshed.active) == 1
    assert refreshed.active[0] in {"A", "B"}
    assert refreshed.used == []


def test_refresh_rotation_bucket_does_not_duplicate_active_species():
    bucket = RotationBucket(queued=["A", "A", "B"], active=["C"], used=["C"])

    refreshed = refresh_rotation_bucket(bucket, ["A", "B", "C"], active_count=3, rng=random.Random(3))

    assert len(refreshed.active) == len(set(refreshed.active))


def test_build_rotation_buckets_returns_queued_candidates_by_frequency():
    chart = SpawnChart(
        area_key="route-alpha",
        entries=[
            SpawnEntry(species_id="A", frequency="frequent", band=1),
            SpawnEntry(species_id="B", frequency="common", band=1),
            SpawnEntry(species_id="C", frequency="rare", band=2),
        ],
    )

    buckets = build_rotation_buckets(chart, 1)

    assert buckets["frequent"].queued == ["A"]
    assert buckets["common"].queued == ["B"]
    assert buckets["rare"].queued == []


def test_roll_spawn_returns_valid_spawn_roll_result():
    chart = SpawnChart(
        area_key="route-alpha",
        entries=[
            SpawnEntry(species_id="025", frequency="frequent", band=1),
            SpawnEntry(species_id="016", frequency="common", band=1),
        ],
    )

    result = roll_spawn(chart, 1, rng=random.Random(9))

    assert isinstance(result, SpawnRollResult)
    assert result.species_id in {"025", "016"}
    assert result.frequency in {SpawnFrequency.FREQUENT.value, SpawnFrequency.COMMON.value}
    assert result.band == 1
    assert 5 <= result.level <= 15


def test_roll_spawn_falls_back_when_frequency_bucket_is_empty():
    chart = SpawnChart(
        area_key="route-alpha",
        entries=[SpawnEntry(species_id="A", frequency="frequent", band=1)],
    )
    rng = random.Random(0)

    assert roll_frequency_for_band(1, random.Random(0)) == "uncommon"
    result = roll_spawn(chart, 1, rng=rng)

    assert result.species_id == "A"
    assert result.frequency == "frequent"


def test_roll_spawn_ignores_special_entries_for_normal_rolls():
    chart = SpawnChart(
        area_key="route-alpha",
        entries=[
            SpawnEntry(species_id="Legend", frequency="special", band=4),
            SpawnEntry(species_id="Common", frequency="common", band=4),
        ],
    )

    results = [roll_spawn(chart, 4, rng=random.Random(seed)).species_id for seed in range(10)]

    assert "Legend" not in results
    assert set(results) == {"Common"}


def test_roll_spawn_raises_when_only_special_entries_exist():
    chart = SpawnChart(
        area_key="route-alpha",
        entries=[SpawnEntry(species_id="Legend", frequency="special", band=4)],
    )

    with pytest.raises(ValueError, match="No normal spawn entries"):
        roll_spawn(chart, 4, rng=random.Random(1))

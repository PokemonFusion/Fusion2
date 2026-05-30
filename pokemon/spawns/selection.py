"""Pure PF2 spawn selection and rotation helpers."""

from __future__ import annotations

import random
from typing import Iterable, Optional, Sequence

from .constants import (
    FREQUENCIES,
    FREQUENCY_WEIGHTS,
    NORMAL_FREQUENCIES,
    SPAWN_BANDS,
    SpawnBandDefinition,
    SpawnFrequency,
)
from .schema import RotationBucket, SpawnChart, SpawnEntry, SpawnRollResult


_FALLBACK_FREQUENCIES = {
    SpawnFrequency.RARE.value: (
        SpawnFrequency.RARE.value,
        SpawnFrequency.UNCOMMON.value,
        SpawnFrequency.COMMON.value,
        SpawnFrequency.FREQUENT.value,
    ),
    SpawnFrequency.UNCOMMON.value: (
        SpawnFrequency.UNCOMMON.value,
        SpawnFrequency.COMMON.value,
        SpawnFrequency.FREQUENT.value,
    ),
    SpawnFrequency.COMMON.value: (
        SpawnFrequency.COMMON.value,
        SpawnFrequency.FREQUENT.value,
    ),
    SpawnFrequency.FREQUENT.value: (
        SpawnFrequency.FREQUENT.value,
        SpawnFrequency.COMMON.value,
        SpawnFrequency.UNCOMMON.value,
        SpawnFrequency.RARE.value,
    ),
}


def _rng_or_default(rng: Optional[random.Random] = None):
    return rng if rng is not None else random


def _unique(items: Iterable[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _pick_many(pool: Sequence[str], count: int, rng=None) -> tuple[list[str], list[str]]:
    rng = _rng_or_default(rng)
    shuffled = list(pool)
    rng.shuffle(shuffled)
    selected = shuffled[:count]
    selected_set = set(selected)
    remaining = [item for item in pool if item not in selected_set]
    return selected, remaining


def _pick_entry(entries: Sequence[SpawnEntry], rng=None) -> SpawnEntry:
    if not entries:
        raise ValueError("Cannot choose from an empty spawn entry list.")
    rng = _rng_or_default(rng)
    return rng.choice(list(entries))


def validate_spawn_entry(entry: SpawnEntry) -> SpawnEntry:
    if not isinstance(entry, SpawnEntry):
        raise TypeError("Spawn entry must be a SpawnEntry.")
    if not isinstance(entry.species_id, str) or not entry.species_id.strip():
        raise ValueError("Spawn entry species_id must be a non-empty string.")
    if entry.frequency not in FREQUENCIES:
        raise ValueError(f"Unknown spawn frequency: {entry.frequency!r}.")
    if entry.band not in SPAWN_BANDS:
        raise ValueError(f"Unknown spawn band: {entry.band!r}.")
    if not isinstance(entry.enabled, bool):
        raise ValueError("Spawn entry enabled must be a boolean.")
    if entry.frequency == SpawnFrequency.SPECIAL.value and entry.band != 4:
        raise ValueError("Special spawn entries are limited to band 4 in Phase 1.")
    return entry


def validate_spawn_chart(chart: SpawnChart) -> SpawnChart:
    if not isinstance(chart, SpawnChart):
        raise TypeError("Spawn chart must be a SpawnChart.")
    if not isinstance(chart.area_key, str) or not chart.area_key.strip():
        raise ValueError("Spawn chart area_key must be a non-empty string.")
    if not isinstance(chart.entries, list):
        raise ValueError("Spawn chart entries must be a list.")
    for entry in chart.entries:
        validate_spawn_entry(entry)
    return chart


def get_band_definition(band: int) -> SpawnBandDefinition:
    try:
        return SPAWN_BANDS[band]
    except KeyError as exc:
        raise ValueError(f"Unknown spawn band: {band!r}.") from exc


def roll_level_for_band(band: int, rng: Optional[random.Random] = None) -> int:
    definition = get_band_definition(band)
    rng = _rng_or_default(rng)
    return rng.randint(definition.min_level, definition.max_level)


def eligible_entries(
    chart: SpawnChart,
    band: int,
    frequency: Optional[str] = None,
) -> list[SpawnEntry]:
    validate_spawn_chart(chart)
    get_band_definition(band)
    if frequency is not None and frequency not in FREQUENCIES:
        raise ValueError(f"Unknown spawn frequency: {frequency!r}.")
    return [
        entry
        for entry in chart.entries
        if entry.enabled and entry.band == band and (frequency is None or entry.frequency == frequency)
    ]


def roll_frequency_for_band(band: int, rng: Optional[random.Random] = None) -> str:
    get_band_definition(band)
    rng = _rng_or_default(rng)
    weights = FREQUENCY_WEIGHTS[band]
    frequencies = [frequency for frequency in NORMAL_FREQUENCIES if weights[frequency] > 0]
    frequency_weights = [weights[frequency] for frequency in frequencies]
    return rng.choices(frequencies, weights=frequency_weights, k=1)[0]


def roll_species_from_entries(entries: Sequence[SpawnEntry], rng: Optional[random.Random] = None) -> str:
    return _pick_entry(entries, rng=rng).species_id


def refresh_rotation_bucket(
    bucket: RotationBucket,
    candidates: Sequence[str],
    active_count: int,
    rng: Optional[random.Random] = None,
) -> RotationBucket:
    if active_count < 0:
        raise ValueError("active_count must not be negative.")

    candidate_list = _unique(str(candidate) for candidate in candidates if str(candidate))
    candidate_set = set(candidate_list)
    if not candidate_list or active_count == 0:
        return RotationBucket(queued=candidate_list, active=[], used=[])

    old_active = [species for species in bucket.active if species in candidate_set]
    used = _unique(
        species
        for species in [*bucket.used, *old_active]
        if species in candidate_set
    )
    queued = _unique(
        species
        for species in bucket.queued
        if species in candidate_set and species not in used
    )
    known = set([*queued, *used])
    queued.extend(species for species in candidate_list if species not in known)

    selected = []
    selected_set = set()
    slots = min(active_count, len(candidate_list))

    while len(selected) < slots:
        if not queued:
            if not used:
                queued = [species for species in candidate_list if species not in selected_set]
            else:
                queued = [species for species in used if species not in selected_set]
                used = []
            if not queued:
                break

        needed = slots - len(selected)
        picked, queued = _pick_many(queued, needed, rng=rng)
        for species in picked:
            if species in selected_set:
                continue
            selected.append(species)
            selected_set.add(species)

    return RotationBucket(queued=queued, active=selected, used=used)


def build_rotation_buckets(chart: SpawnChart, band: int) -> dict[str, RotationBucket]:
    validate_spawn_chart(chart)
    return {
        frequency: RotationBucket(
            queued=[entry.species_id for entry in eligible_entries(chart, band, frequency=frequency)],
            active=[],
            used=[],
        )
        for frequency in FREQUENCIES
    }


def select_active_species(bucket: RotationBucket, rng: Optional[random.Random] = None) -> str:
    if not bucket.active:
        raise ValueError("Cannot choose from an empty active spawn bucket.")
    rng = _rng_or_default(rng)
    return rng.choice(bucket.active)


def roll_spawn(chart: SpawnChart, band: int, rng: Optional[random.Random] = None) -> SpawnRollResult:
    validate_spawn_chart(chart)
    get_band_definition(band)
    rng = _rng_or_default(rng)
    rolled_frequency = roll_frequency_for_band(band, rng=rng)

    # Special spawns are intentionally outside the normal frequency roll.
    # Live cooldown and pity logic belongs in a later hunt integration phase.
    for frequency in _FALLBACK_FREQUENCIES[rolled_frequency]:
        entries = eligible_entries(chart, band, frequency=frequency)
        if not entries:
            continue
        entry = _pick_entry(entries, rng=rng)
        return SpawnRollResult(
            species_id=entry.species_id,
            frequency=entry.frequency,
            band=band,
            level=roll_level_for_band(band, rng=rng),
        )

    raise ValueError(f"No normal spawn entries are available for band {band}.")

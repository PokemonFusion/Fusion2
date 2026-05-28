"""Dry-run helpers for probing PF2 spawn rolls without live hunt effects."""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass
from typing import Optional

from .constants import NORMAL_FREQUENCIES, SPAWN_BANDS, SpawnFrequency
from .schema import SpawnChart
from .selection import eligible_entries, roll_spawn


DEFAULT_ROLL_TEST_BAND = 1
DEFAULT_ROLL_TEST_COUNT = 20
MAX_ROLL_TEST_COUNT = 200
TOP_SPECIES_LIMIT = 12


@dataclass(frozen=True)
class SpawnRollTestOptions:
    band: int = DEFAULT_ROLL_TEST_BAND
    count: int = DEFAULT_ROLL_TEST_COUNT
    requested_count: int = DEFAULT_ROLL_TEST_COUNT


@dataclass(frozen=True)
class SpawnRollTestResult:
    area_key: str
    band: int
    requested_count: int
    roll_count: int
    successful_rolls: int
    frequency_counts: Counter[str]
    species_counts: Counter[str]
    error: str = ""


def parse_rolltest_args(raw_args: str | None) -> SpawnRollTestOptions:
    parts = (raw_args or "").split()
    if len(parts) > 2:
        raise ValueError("Usage: @spawnrolltest [band] [count]")

    band = DEFAULT_ROLL_TEST_BAND
    count = DEFAULT_ROLL_TEST_COUNT
    if parts:
        band = _parse_band(parts[0])
    if len(parts) == 2:
        count = _parse_count(parts[1])

    requested_count = count
    count = min(count, MAX_ROLL_TEST_COUNT)
    return SpawnRollTestOptions(band=band, count=count, requested_count=requested_count)


def run_spawn_roll_test(
    chart: SpawnChart,
    *,
    band: int,
    count: int,
    requested_count: Optional[int] = None,
    rng: Optional[random.Random] = None,
) -> SpawnRollTestResult:
    if band not in SPAWN_BANDS:
        raise ValueError("Band must be a number from 1 to 4.")
    if count < 1:
        raise ValueError("Count must be a positive number.")

    requested = requested_count if requested_count is not None else count
    rng = rng if rng is not None else random
    if not _has_normal_entries(chart, band):
        return SpawnRollTestResult(
            area_key=chart.area_key,
            band=band,
            requested_count=requested,
            roll_count=count,
            successful_rolls=0,
            frequency_counts=Counter(),
            species_counts=Counter(),
            error=f"No normal spawn entries are available for band {band}.",
        )

    frequency_counts: Counter[str] = Counter()
    species_counts: Counter[str] = Counter()
    for _ in range(count):
        result = roll_spawn(chart, band, rng=rng)
        frequency_counts[result.frequency] += 1
        species_counts[result.species_id] += 1

    return SpawnRollTestResult(
        area_key=chart.area_key,
        band=band,
        requested_count=requested,
        roll_count=count,
        successful_rolls=sum(species_counts.values()),
        frequency_counts=frequency_counts,
        species_counts=species_counts,
    )


def format_spawn_roll_test(result: SpawnRollTestResult, *, source: str) -> str:
    lines = [
        "PF2 Spawn Roll Test",
        f"Area key: {result.area_key}",
        f"Source: {source}",
        f"Band: {result.band}",
        _roll_count_line(result),
        f"Successful rolls: {result.successful_rolls}",
        "Special entries are configured only; normal roll tests ignore special.",
    ]
    if result.error:
        lines.append(result.error)
        return "\n".join(lines)

    lines.append("Frequency breakdown:")
    for frequency in NORMAL_FREQUENCIES:
        count = result.frequency_counts.get(frequency, 0)
        if count:
            lines.append(f"  {frequency}: {count}")
    if not result.frequency_counts:
        lines.append("  none")

    lines.append("Top species:")
    for species_id, count in _top_species(result):
        lines.append(f"  {species_id}: {count}")
    return "\n".join(lines)


def _parse_band(value: str) -> int:
    try:
        band = int(value)
    except ValueError as exc:
        raise ValueError("Band must be a number from 1 to 4.") from exc
    if band not in SPAWN_BANDS:
        raise ValueError("Band must be a number from 1 to 4.")
    return band


def _parse_count(value: str) -> int:
    try:
        count = int(value)
    except ValueError as exc:
        raise ValueError("Count must be a positive number.") from exc
    if count < 1:
        raise ValueError("Count must be a positive number.")
    return count


def _has_normal_entries(chart: SpawnChart, band: int) -> bool:
    return any(
        eligible_entries(chart, band, frequency=frequency)
        for frequency in NORMAL_FREQUENCIES
        if frequency != SpawnFrequency.SPECIAL.value
    )


def _roll_count_line(result: SpawnRollTestResult) -> str:
    if result.requested_count != result.roll_count:
        return f"Roll count: {result.roll_count} (clamped from {result.requested_count})"
    return f"Roll count: {result.roll_count}"


def _top_species(result: SpawnRollTestResult) -> list[tuple[str, int]]:
    top = sorted(result.species_counts.items(), key=lambda item: (-item[1], item[0]))
    return top[:TOP_SPECIES_LIMIT]

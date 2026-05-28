"""Roll-test helpers for file-backed PF2 spawn profile data."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Optional

from .profile_data import resolve_sample_area
from .rolltest import (
    DEFAULT_ROLL_TEST_BAND,
    DEFAULT_ROLL_TEST_COUNT,
    MAX_ROLL_TEST_COUNT,
    SpawnRollTestResult,
    run_spawn_roll_test,
)
from .schema import SpawnChart


PROFILE_ROLL_TEST_SOURCE = "profile sample data"


@dataclass(frozen=True)
class ProfileRollTestOptions:
    area_key: str
    band: int = DEFAULT_ROLL_TEST_BAND
    count: int = DEFAULT_ROLL_TEST_COUNT
    requested_count: int = DEFAULT_ROLL_TEST_COUNT


def parse_profile_rolltest_args(raw_args: str | None) -> ProfileRollTestOptions:
    parts = (raw_args or "").split()
    if not parts or len(parts) > 3:
        raise ValueError("Usage: @spawnprofilerolltest <area_key> [band] [count]")

    area_key = parts[0].strip()
    if not area_key:
        raise ValueError("Usage: @spawnprofilerolltest <area_key> [band] [count]")

    band = DEFAULT_ROLL_TEST_BAND
    count = DEFAULT_ROLL_TEST_COUNT
    if len(parts) >= 2:
        band = _parse_band(parts[1])
    if len(parts) == 3:
        count = _parse_count(parts[2])

    requested_count = count
    count = min(count, MAX_ROLL_TEST_COUNT)
    return ProfileRollTestOptions(
        area_key=area_key,
        band=band,
        count=count,
        requested_count=requested_count,
    )


def run_profile_spawn_roll_test(
    area_key: str,
    *,
    band: int = DEFAULT_ROLL_TEST_BAND,
    count: int = DEFAULT_ROLL_TEST_COUNT,
    requested_count: Optional[int] = None,
    rng: Optional[random.Random] = None,
    chart_resolver: Callable[[str], SpawnChart] = resolve_sample_area,
) -> SpawnRollTestResult:
    chart = chart_resolver(area_key)
    return run_spawn_roll_test(
        chart,
        band=band,
        count=count,
        requested_count=requested_count,
        rng=rng,
    )


def _parse_band(value: str) -> int:
    try:
        band = int(value)
    except ValueError as exc:
        raise ValueError("Band must be a number from 1 to 4.") from exc
    if band not in {1, 2, 3, 4}:
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

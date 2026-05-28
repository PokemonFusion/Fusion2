"""Profile-backed wild battle test helpers for staff-only commands."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Optional

from .hunttest import (
    DEFAULT_SPAWN_HUNT_TEST_BAND,
    SpawnHuntTestError,
    SpawnHuntTestResult,
    run_spawn_hunt_test,
)
from .profile_data import resolve_sample_area
from .schema import SpawnChart


@dataclass(frozen=True)
class ProfileHuntTestOptions:
    area_key: str
    band: int = DEFAULT_SPAWN_HUNT_TEST_BAND


def parse_profile_hunttest_args(raw_args: str | None) -> ProfileHuntTestOptions:
    parts = (raw_args or "").split()
    if not parts or len(parts) > 2:
        raise ValueError("Usage: @spawnprofilehunttest <area_key> [band]")

    area_key = parts[0].strip()
    if not area_key:
        raise ValueError("Usage: @spawnprofilehunttest <area_key> [band]")

    band = DEFAULT_SPAWN_HUNT_TEST_BAND
    if len(parts) == 2:
        band = _parse_band(parts[1])
    return ProfileHuntTestOptions(area_key=area_key, band=band)


def run_profile_spawn_hunt_test(
    caller,
    area_key: str,
    *,
    band: int = DEFAULT_SPAWN_HUNT_TEST_BAND,
    rng: Optional[random.Random] = None,
    chart_resolver: Callable[[str], SpawnChart] = resolve_sample_area,
    battle_session_cls=None,
) -> SpawnHuntTestResult:
    chart = chart_resolver(area_key)
    kwargs = {"band": band, "rng": rng}
    if battle_session_cls is not None:
        kwargs["battle_session_cls"] = battle_session_cls
    return run_spawn_hunt_test(caller, chart, **kwargs)


def _parse_band(value: str) -> int:
    try:
        band = int(value)
    except ValueError as exc:
        raise ValueError("Band must be a number from 1 to 4.") from exc
    if band not in {1, 2, 3, 4}:
        raise ValueError("Band must be a number from 1 to 4.")
    return band

"""Pure special-spawn pity and cooldown helpers."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from .constants import SpawnFrequency
from .schema import SpawnChart, SpawnEntry, SpawnRollResult
from .selection import eligible_entries, roll_level_for_band


SPECIAL_REQUIRED_BAND = 4
SPECIAL_COOLDOWN_SECONDS = 86400
SPECIAL_BASE_DENOMINATOR = 10000
SPECIAL_PITY_STEP = 225
SPECIAL_PITY_CAP_TICKS = 40
SPECIAL_MIN_DENOMINATOR = 1000


@dataclass(frozen=True)
class SpecialSpawnState:
    current_time: int
    last_special_at: Optional[int] = None
    current_tick: int = 0
    last_special_tick: int = 0
    ignore_special_finder: bool = False


def _rng_or_default(rng: Optional[random.Random] = None):
    return rng if rng is not None else random


def eligible_special_entries(chart: SpawnChart, band: int) -> list[SpawnEntry]:
    """Return enabled configured specials for the required special band only."""

    if band != SPECIAL_REQUIRED_BAND:
        return []
    return eligible_entries(chart, band, frequency=SpawnFrequency.SPECIAL.value)


def special_cooldown_remaining(state: SpecialSpawnState) -> int:
    if state.last_special_at is None:
        return 0
    elapsed = max(0, int(state.current_time) - int(state.last_special_at))
    return max(0, SPECIAL_COOLDOWN_SECONDS - elapsed)


def special_pity_ticks(state: SpecialSpawnState) -> int:
    tickdiff = max(0, int(state.current_tick) - int(state.last_special_tick))
    return min(SPECIAL_PITY_CAP_TICKS, tickdiff)


def special_roll_denominator(state: SpecialSpawnState) -> int:
    denominator = SPECIAL_BASE_DENOMINATOR - special_pity_ticks(state) * SPECIAL_PITY_STEP
    return max(SPECIAL_MIN_DENOMINATOR, denominator)


def passes_special_roll(state: SpecialSpawnState, rng: Optional[random.Random] = None) -> bool:
    rng = _rng_or_default(rng)
    return rng.randrange(special_roll_denominator(state)) == 0


def roll_special_spawn(
    chart: SpawnChart,
    band: int,
    state: SpecialSpawnState,
    rng: Optional[random.Random] = None,
) -> Optional[SpawnRollResult]:
    """Roll a special spawn without mutating player, room, or hunt state."""

    if band != SPECIAL_REQUIRED_BAND:
        return None
    if state.ignore_special_finder:
        return None
    if special_cooldown_remaining(state) > 0:
        return None

    entries = eligible_special_entries(chart, band)
    if not entries:
        return None

    rng = _rng_or_default(rng)
    if not passes_special_roll(state, rng=rng):
        return None

    entry = rng.choice(entries)
    return SpawnRollResult(
        species_id=entry.species_id,
        frequency=SpawnFrequency.SPECIAL.value,
        band=band,
        level=roll_level_for_band(band, rng=rng),
    )

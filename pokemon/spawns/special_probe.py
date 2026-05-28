"""Read-only helpers for probing PF2 special spawn eligibility."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Optional

from .preview import DEFAULT_GROUP_LIMIT, format_species_group
from .profile_data import resolve_sample_area
from .schema import SpawnChart, SpawnRollResult
from .specials import (
    SPECIAL_COOLDOWN_SECONDS,
    SPECIAL_REQUIRED_BAND,
    SpecialSpawnState,
    eligible_special_entries,
    roll_special_spawn,
    special_cooldown_remaining,
    special_pity_ticks,
    special_roll_denominator,
)


SPECIAL_PROBE_ROOM_SOURCE = "room"
SPECIAL_PROBE_PROFILE_SOURCE = "profile"
DEFAULT_SPECIAL_PROBE_CURRENT_TICK = 0
DEFAULT_SPECIAL_PROBE_LAST_SPECIAL_TICK = 0
DEFAULT_SPECIAL_PROBE_SECONDS_SINCE_LAST_SPECIAL = SPECIAL_COOLDOWN_SECONDS
SPECIAL_PROBE_USAGE = (
    "Usage: @spawnspecialprobe room [current_tick] [last_special_tick] "
    "[seconds_since_last_special] OR @spawnspecialprobe profile <area_key> "
    "[current_tick] [last_special_tick] [seconds_since_last_special]"
)


@dataclass(frozen=True)
class SpecialProbeOptions:
    source: str
    area_key: Optional[str]
    state: SpecialSpawnState


@dataclass(frozen=True)
class SpecialProbeResult:
    source: str
    area_key: str
    special_entry_count: int
    eligible_species: tuple[str, ...]
    cooldown_remaining: int
    pity_ticks: int
    roll_denominator: int
    roll_passed: bool
    spawn_result: Optional[SpawnRollResult] = None
    blocked_reason: str = ""


def parse_special_probe_args(raw_args: str | None) -> SpecialProbeOptions:
    parts = (raw_args or "").split()
    if not parts:
        raise ValueError(SPECIAL_PROBE_USAGE)

    source = parts[0].strip().lower()
    if source == SPECIAL_PROBE_ROOM_SOURCE:
        if len(parts) > 4:
            raise ValueError(SPECIAL_PROBE_USAGE)
        state = build_special_probe_state(parts[1:])
        return SpecialProbeOptions(source=source, area_key=None, state=state)

    if source == SPECIAL_PROBE_PROFILE_SOURCE:
        if len(parts) < 2 or len(parts) > 5:
            raise ValueError(SPECIAL_PROBE_USAGE)
        area_key = parts[1].strip()
        if not area_key:
            raise ValueError(SPECIAL_PROBE_USAGE)
        state = build_special_probe_state(parts[2:])
        return SpecialProbeOptions(source=source, area_key=area_key, state=state)

    raise ValueError(SPECIAL_PROBE_USAGE)


def build_special_probe_state(values: list[str] | tuple[str, ...]) -> SpecialSpawnState:
    current_tick = DEFAULT_SPECIAL_PROBE_CURRENT_TICK
    last_special_tick = DEFAULT_SPECIAL_PROBE_LAST_SPECIAL_TICK
    seconds_since_last_special = DEFAULT_SPECIAL_PROBE_SECONDS_SINCE_LAST_SPECIAL

    if len(values) >= 1:
        current_tick = _parse_non_negative_int(values[0], "current_tick")
    if len(values) >= 2:
        last_special_tick = _parse_non_negative_int(values[1], "last_special_tick")
    if len(values) >= 3:
        seconds_since_last_special = _parse_non_negative_int(values[2], "seconds_since_last_special")

    return SpecialSpawnState(
        current_time=seconds_since_last_special,
        last_special_at=0,
        current_tick=current_tick,
        last_special_tick=last_special_tick,
    )


def run_special_spawn_probe(
    chart: SpawnChart,
    *,
    source: str,
    state: SpecialSpawnState,
    rng: Optional[random.Random] = None,
) -> SpecialProbeResult:
    entries = eligible_special_entries(chart, SPECIAL_REQUIRED_BAND)
    species = tuple(entry.species_id for entry in entries)
    cooldown_remaining = special_cooldown_remaining(state)
    roll_denominator = special_roll_denominator(state)
    result = roll_special_spawn(chart, SPECIAL_REQUIRED_BAND, state, rng=rng)
    blocked_reason = _blocked_reason(
        special_entry_count=len(entries),
        cooldown_remaining=cooldown_remaining,
        state=state,
    )

    return SpecialProbeResult(
        source=source,
        area_key=chart.area_key,
        special_entry_count=len(entries),
        eligible_species=species,
        cooldown_remaining=cooldown_remaining,
        pity_ticks=special_pity_ticks(state),
        roll_denominator=roll_denominator,
        roll_passed=result is not None,
        spawn_result=result,
        blocked_reason=blocked_reason,
    )


def run_profile_special_spawn_probe(
    area_key: str,
    *,
    state: SpecialSpawnState,
    rng: Optional[random.Random] = None,
    chart_resolver: Callable[[str], SpawnChart] = resolve_sample_area,
) -> SpecialProbeResult:
    chart = chart_resolver(area_key)
    return run_special_spawn_probe(
        chart,
        source=SPECIAL_PROBE_PROFILE_SOURCE,
        state=state,
        rng=rng,
    )


def format_special_spawn_probe(
    result: SpecialProbeResult,
    *,
    group_limit: int = DEFAULT_GROUP_LIMIT,
) -> str:
    lines = [
        "PF2 Special Spawn Probe",
        f"Source: {result.source}",
        f"Area key: {result.area_key}",
        f"Band: {SPECIAL_REQUIRED_BAND} (specials only)",
        f"Special entry count: {result.special_entry_count}",
        f"Eligible specials: {format_species_group(result.eligible_species, group_limit)}",
        f"Cooldown remaining: {result.cooldown_remaining} seconds",
        f"Pity ticks: {result.pity_ticks}",
        f"Roll denominator: 1/{result.roll_denominator} ({_chance_percent(result.roll_denominator)})",
    ]

    if result.spawn_result:
        lines.extend(
            [
                "Simulated roll: passed",
                f"Selected special: {result.spawn_result.species_id} level {result.spawn_result.level}",
            ]
        )
    elif result.blocked_reason:
        lines.extend(
            [
                f"Simulated roll: blocked ({result.blocked_reason})",
                "No special would spawn.",
            ]
        )
    else:
        lines.extend(["Simulated roll: failed", "No special would spawn."])

    lines.append("No state was modified and no battle was started.")
    return "\n".join(lines)


def _parse_non_negative_int(value: str, label: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be a non-negative integer.") from exc
    if number < 0:
        raise ValueError(f"{label} must be a non-negative integer.")
    return number


def _blocked_reason(
    *,
    special_entry_count: int,
    cooldown_remaining: int,
    state: SpecialSpawnState,
) -> str:
    if not special_entry_count:
        return "no eligible band 4 special entries"
    if state.ignore_special_finder:
        return "special finder is ignored"
    if cooldown_remaining > 0:
        return "cooldown active"
    return ""


def _chance_percent(denominator: int) -> str:
    return f"{100 / denominator:.2f}%"

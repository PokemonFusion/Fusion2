"""Plain-text preview formatting for PF2 spawn charts."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from .constants import FREQUENCIES, SPAWN_BANDS, SpawnFrequency
from .schema import SpawnChart, SpawnEntry


DEFAULT_GROUP_LIMIT = 12


def parse_preview_band(raw_value: str | None) -> int | None:
    value = (raw_value or "").strip()
    if not value:
        return None
    try:
        band = int(value)
    except ValueError as exc:
        raise ValueError("Band must be a number from 1 to 4.") from exc
    if band not in SPAWN_BANDS:
        raise ValueError("Band must be a number from 1 to 4.")
    return band


def format_species_group(species_ids: Iterable[str], limit: int = DEFAULT_GROUP_LIMIT) -> str:
    species = list(species_ids)
    if not species:
        return "-"
    shown = species[:limit]
    text = ", ".join(shown)
    remaining = len(species) - len(shown)
    if remaining > 0:
        text = f"{text}, ... (+{remaining} more)"
    return text


def format_spawn_preview(
    chart: SpawnChart,
    *,
    source: str,
    band: int | None = None,
    group_limit: int = DEFAULT_GROUP_LIMIT,
) -> str:
    entries = [entry for entry in chart.entries if band is None or entry.band == band]
    lines = [
        "PF2 Spawn Preview",
        f"Area key: {chart.area_key}",
        f"Source: {source}",
        f"Total converted entries: {len(chart.entries)}",
    ]
    if band is not None:
        lines.append(f"Band filter: {band} ({len(entries)} shown)")
    lines.append("Special entries are configured only; normal roll ignores special in Phase 1.")

    if not entries:
        lines.append("No converted spawn entries were found.")
        return "\n".join(lines)

    grouped = _group_entries(entries)
    for entry_band in sorted(grouped):
        lines.append(f"Band {entry_band}")
        for frequency in FREQUENCIES:
            active_species = grouped[entry_band]["enabled"].get(frequency, [])
            disabled_species = grouped[entry_band]["disabled"].get(frequency, [])
            if not active_species and not disabled_species:
                continue
            label = frequency
            if frequency == SpawnFrequency.SPECIAL.value:
                label = "special (not normal roll)"
            if active_species:
                lines.append(f"  {label}: {format_species_group(active_species, group_limit)}")
            if disabled_species:
                lines.append(f"  {label} disabled: {format_species_group(disabled_species, group_limit)}")

    return "\n".join(lines)


def _group_entries(entries: Iterable[SpawnEntry]):
    grouped = defaultdict(lambda: {"enabled": defaultdict(list), "disabled": defaultdict(list)})
    for entry in entries:
        state = "enabled" if entry.enabled else "disabled"
        grouped[entry.band][state][entry.frequency].append(entry.species_id)
    return grouped

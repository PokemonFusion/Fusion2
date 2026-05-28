"""Read-only comparison between live hunt data and PF2 spawn adapters."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from utils.pokemon_config import TIERS as LIVE_TIERS

from .adapters import spawn_chart_from_room
from .preview import format_species_group
from .schema import SpawnChart, SpawnEntry


class SpawnCompareError(ValueError):
    """Raised when live room spawn data cannot be interpreted safely."""


@dataclass(frozen=True)
class ComparableSpawnEntry:
    species_id: str
    frequency: str
    bands: tuple[str, ...]
    enabled: bool = True


@dataclass(frozen=True)
class SpawnDifference:
    species_id: str
    live: tuple[str, ...]
    new: tuple[str, ...]


@dataclass(frozen=True)
class SpawnComparison:
    area_key: str
    source: str
    band: int | None
    live_entry_count: int
    new_entry_count: int
    species_in_both: tuple[str, ...]
    species_only_live: tuple[str, ...]
    species_only_new: tuple[str, ...]
    frequency_differences: tuple[SpawnDifference, ...] = field(default_factory=tuple)
    band_differences: tuple[SpawnDifference, ...] = field(default_factory=tuple)
    special_species: tuple[str, ...] = field(default_factory=tuple)


def compare_room_spawns(room: Any, band: int | None = None) -> SpawnComparison:
    chart = spawn_chart_from_room(room)
    source = detect_spawn_source(room)
    live_entries = live_spawn_entries_from_room(room)
    new_entries = comparable_entries_from_chart(chart)
    return compare_spawn_entries(
        area_key=chart.area_key,
        source=source,
        live_entries=live_entries,
        new_entries=new_entries,
        band=band,
    )


def detect_spawn_source(room: Any) -> str:
    db = getattr(room, "db", None)
    if getattr(db, "hunt_chart", None):
        return "hunt_chart"
    if getattr(db, "spawn_table", None):
        return "spawn_table"
    return "empty"


def live_spawn_entries_from_room(room: Any) -> list[ComparableSpawnEntry]:
    db = getattr(room, "db", None)
    data = getattr(db, "hunt_chart", None) or getattr(db, "spawn_table", None) or []
    if not isinstance(data, list):
        raise SpawnCompareError("Live spawn data must be a list of entry dictionaries.")

    entries: list[ComparableSpawnEntry] = []
    for raw_entry in data:
        if not isinstance(raw_entry, dict):
            raise SpawnCompareError("Live spawn data entries must be dictionaries.")
        species_id = _normalize_live_species(raw_entry.get("name") or raw_entry.get("species"))
        if not species_id:
            continue
        entries.append(
            ComparableSpawnEntry(
                species_id=species_id,
                frequency=_normalize_live_frequency(raw_entry),
                bands=_live_band_labels(raw_entry),
            )
        )
    return entries


def comparable_entries_from_chart(chart: SpawnChart) -> list[ComparableSpawnEntry]:
    return [comparable_entry_from_spawn_entry(entry) for entry in chart.entries]


def comparable_entry_from_spawn_entry(entry: SpawnEntry) -> ComparableSpawnEntry:
    return ComparableSpawnEntry(
        species_id=entry.species_id,
        frequency=entry.frequency,
        bands=(f"B{entry.band}",),
        enabled=entry.enabled,
    )


def compare_spawn_entries(
    *,
    area_key: str,
    source: str,
    live_entries: Iterable[ComparableSpawnEntry],
    new_entries: Iterable[ComparableSpawnEntry],
    band: int | None = None,
) -> SpawnComparison:
    live_filtered = _filter_by_band(live_entries, band)
    new_filtered = _filter_by_band(new_entries, band)
    live_index = _index_entries(live_filtered)
    new_index = _index_entries(new_filtered)
    live_species = set(live_index)
    new_species = set(new_index)
    both = tuple(sorted(live_species & new_species))

    return SpawnComparison(
        area_key=area_key,
        source=source,
        band=band,
        live_entry_count=len(live_filtered),
        new_entry_count=len(new_filtered),
        species_in_both=both,
        species_only_live=tuple(sorted(live_species - new_species)),
        species_only_new=tuple(sorted(new_species - live_species)),
        frequency_differences=_differences(both, live_index, new_index, "frequencies"),
        band_differences=_differences(both, live_index, new_index, "bands"),
        special_species=_special_species(new_index),
    )


def format_spawn_comparison(comparison: SpawnComparison, limit: int = 12) -> str:
    lines = [
        "PF2 Spawn Compare",
        f"Area key: {comparison.area_key}",
        f"Source: {comparison.source}",
        f"Band: {comparison.band if comparison.band is not None else 'all'}",
        f"Live interpreted entries: {comparison.live_entry_count}",
        f"New adapter entries: {comparison.new_entry_count}",
        "Special entries are configured only; normal roll tests ignore special.",
    ]

    if comparison.live_entry_count == 0 and comparison.new_entry_count == 0:
        lines.append("No live or new spawn entries were found.")
        return "\n".join(lines)

    lines.extend(
        [
            f"Species in both: {format_species_group(comparison.species_in_both, limit)}",
            f"Only live: {format_species_group(comparison.species_only_live, limit)}",
            f"Only new: {format_species_group(comparison.species_only_new, limit)}",
        ]
    )
    if comparison.special_species:
        lines.append(f"Special configured: {format_species_group(comparison.special_species, limit)}")
    _append_differences(lines, "Frequency differences", comparison.frequency_differences, limit)
    _append_differences(lines, "Band/tier differences", comparison.band_differences, limit)
    return "\n".join(lines)


def _normalize_live_species(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _normalize_live_frequency(entry: dict[str, Any]) -> str:
    value = entry.get("rarity", "common")
    text = str(value).strip().lower() if value is not None else ""
    return text or "common"


def _live_band_labels(entry: dict[str, Any]) -> tuple[str, ...]:
    values = _as_values(entry.get("tiers", ["T1"]))
    live_tiers = [str(value).strip() for value in values if str(value).strip() in LIVE_TIERS]
    if not live_tiers:
        live_tiers = ["T1"]
    return tuple(_tier_label(tier) for tier in live_tiers)


def _tier_label(tier: str) -> str:
    if len(tier) == 2 and tier[0].upper() == "T" and tier[1] in {"1", "2", "3", "4"}:
        return f"B{tier[1]}"
    return tier


def _as_values(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [value]
    try:
        return list(value)
    except TypeError:
        return [value]


def _filter_by_band(entries: Iterable[ComparableSpawnEntry], band: int | None) -> list[ComparableSpawnEntry]:
    entries = list(entries)
    if band is None:
        return entries
    label = f"B{band}"
    return [entry for entry in entries if label in entry.bands]


def _index_entries(entries: Iterable[ComparableSpawnEntry]):
    index = defaultdict(lambda: {"frequencies": set(), "bands": set()})
    for entry in entries:
        if not entry.enabled:
            continue
        item = index[entry.species_id]
        item["frequencies"].add(entry.frequency)
        item["bands"].update(entry.bands)
    return index


def _differences(species_ids, live_index, new_index, field_name: str) -> tuple[SpawnDifference, ...]:
    results = []
    for species_id in species_ids:
        live = tuple(sorted(live_index[species_id][field_name]))
        new = tuple(sorted(new_index[species_id][field_name]))
        if live != new:
            results.append(SpawnDifference(species_id=species_id, live=live, new=new))
    return tuple(results)


def _special_species(new_index) -> tuple[str, ...]:
    return tuple(
        sorted(
            species_id
            for species_id, values in new_index.items()
            if "special" in values["frequencies"]
        )
    )


def _append_differences(lines: list[str], title: str, differences, limit: int) -> None:
    if not differences:
        lines.append(f"{title}: none")
        return
    lines.append(f"{title}:")
    shown = differences[:limit]
    for diff in shown:
        lines.append(f"  {diff.species_id}: live {', '.join(diff.live)}; new {', '.join(diff.new)}")
    remaining = len(differences) - len(shown)
    if remaining > 0:
        lines.append(f"  ... (+{remaining} more)")

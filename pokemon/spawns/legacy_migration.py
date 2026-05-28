"""Read-only audit helpers for legacy room hunt_chart migration planning."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from .adapters import SpawnAdapterError, normalize_band, normalize_frequency
from .constants import SPAWN_BANDS, SpawnFrequency


DEFAULT_AUDIT_ENTRY_LIMIT = 12


@dataclass
class LegacyHuntEntryAudit:
    species_id: str
    original_weight: int | None
    original_min_level: int | None
    original_max_level: int | None
    existing_frequency: str | None
    existing_tiers: list[int]
    recommended_frequency: str | None
    recommended_bands: list[int]
    warnings: list[str] = field(default_factory=list)


@dataclass
class LegacyHuntChartAudit:
    area_key: str
    entries: list[LegacyHuntEntryAudit]
    warnings: list[str] = field(default_factory=list)


def recommend_frequency_from_weight(weight) -> str | None:
    value = _coerce_int(weight)
    if value is None:
        return None
    if value >= 60:
        return SpawnFrequency.FREQUENT.value
    if value >= 30:
        return SpawnFrequency.COMMON.value
    if value >= 10:
        return SpawnFrequency.UNCOMMON.value
    return SpawnFrequency.RARE.value


def recommend_bands_from_level_range(min_level, max_level) -> list[int]:
    low = _coerce_int(min_level)
    high = _coerce_int(max_level)
    if low is None or high is None or high < low:
        return []

    for band, definition in SPAWN_BANDS.items():
        if low >= definition.min_level and high <= definition.max_level:
            return [band]

    return [
        band
        for band, definition in SPAWN_BANDS.items()
        if low <= definition.max_level and high >= definition.min_level
    ]


def audit_legacy_hunt_chart(data, area_key: str = "unknown") -> LegacyHuntChartAudit:
    chart_warnings: list[str] = []
    entries: list[LegacyHuntEntryAudit] = []
    normalized_area_key = str(area_key).strip() or "unknown"

    if data is None:
        return LegacyHuntChartAudit(
            area_key=normalized_area_key,
            entries=[],
            warnings=["No legacy hunt_chart data found."],
        )
    if not isinstance(data, list):
        return LegacyHuntChartAudit(
            area_key=normalized_area_key,
            entries=[],
            warnings=["Legacy hunt_chart data must be a list of entry dictionaries."],
        )
    if not data:
        chart_warnings.append("No legacy hunt_chart entries found.")

    for index, raw_entry in enumerate(data, start=1):
        if not isinstance(raw_entry, dict):
            chart_warnings.append(f"Entry #{index} is not a dictionary and was skipped.")
            continue
        audit = _audit_entry(raw_entry)
        if not audit.species_id:
            chart_warnings.append(f"Entry #{index} is missing a species id.")
        entries.append(audit)

    return LegacyHuntChartAudit(
        area_key=normalized_area_key,
        entries=entries,
        warnings=chart_warnings,
    )


def format_legacy_hunt_chart_audit(
    audit: LegacyHuntChartAudit,
    *,
    limit: int = DEFAULT_AUDIT_ENTRY_LIMIT,
) -> str:
    lines = [
        "PF2 Legacy Hunt Chart Migration Audit",
        f"Area key: {audit.area_key}",
        f"Total legacy entries: {len(audit.entries)}",
        "Recommendations are read-only; no room data was modified.",
    ]

    if audit.warnings:
        lines.append("Chart warnings:")
        lines.extend(f"  {warning}" for warning in audit.warnings)

    if not audit.entries:
        lines.append("No legacy entries to audit.")
        return "\n".join(lines)

    lines.append("Entries:")
    shown = audit.entries[:limit]
    for entry in shown:
        lines.append(f"  {_entry_line(entry)}")
        for warning in entry.warnings:
            lines.append(f"    warning: {warning}")

    remaining = len(audit.entries) - len(shown)
    if remaining > 0:
        lines.append(f"  ... (+{remaining} more entries)")

    return "\n".join(lines)


def _audit_entry(entry: dict[str, Any]) -> LegacyHuntEntryAudit:
    warnings: list[str] = []
    species_id = _species_id(entry)
    if not species_id:
        warnings.append("Missing species id.")

    original_weight = _coerce_int(entry.get("weight"))
    if "weight" not in entry or original_weight is None:
        warnings.append("Missing or invalid weight; no frequency recommendation from weight.")
    recommended_frequency = recommend_frequency_from_weight(original_weight)

    existing_frequency = _existing_frequency(entry, warnings)
    if existing_frequency and recommended_frequency and existing_frequency != recommended_frequency:
        warnings.append("Existing frequency differs from weight recommendation.")

    original_min_level = _coerce_int(entry.get("min_level"))
    original_max_level = _coerce_int(entry.get("max_level"))
    recommended_bands = _recommended_bands(entry, original_min_level, original_max_level, warnings)
    existing_tiers = _existing_tiers(entry, warnings)
    if existing_tiers and recommended_bands and sorted(existing_tiers) != recommended_bands:
        warnings.append("Existing tiers differ from level-range recommendation.")

    return LegacyHuntEntryAudit(
        species_id=species_id,
        original_weight=original_weight,
        original_min_level=original_min_level,
        original_max_level=original_max_level,
        existing_frequency=existing_frequency,
        existing_tiers=existing_tiers,
        recommended_frequency=recommended_frequency,
        recommended_bands=recommended_bands,
        warnings=warnings,
    )


def _species_id(entry: dict[str, Any]) -> str:
    value = entry.get("species") or entry.get("name")
    return str(value).strip() if value is not None else ""


def _existing_frequency(entry: dict[str, Any], warnings: list[str]) -> str | None:
    if "frequency" in entry:
        raw_frequency = entry.get("frequency")
    elif "rarity" in entry:
        raw_frequency = entry.get("rarity")
    else:
        return None

    if raw_frequency is None or str(raw_frequency).strip() == "":
        warnings.append("Existing frequency/rarity is blank.")
        return None
    try:
        return normalize_frequency(raw_frequency)
    except SpawnAdapterError:
        warnings.append(f"Invalid existing frequency/rarity: {raw_frequency!r}.")
        return None


def _existing_tiers(entry: dict[str, Any], warnings: list[str]) -> list[int]:
    for key in ("tiers", "tier", "bands", "band"):
        if key not in entry:
            continue
        tiers: list[int] = []
        for value in _as_values(entry.get(key)):
            try:
                tiers.append(normalize_band(value))
            except SpawnAdapterError:
                warnings.append(f"Invalid existing tier/band: {value!r}.")
        return _unique_sorted(tiers)
    return []


def _recommended_bands(
    entry: dict[str, Any],
    min_level: int | None,
    max_level: int | None,
    warnings: list[str],
) -> list[int]:
    if "min_level" not in entry or "max_level" not in entry or min_level is None or max_level is None:
        warnings.append("Missing or invalid min_level/max_level; no band recommendation from levels.")
        return []
    if max_level < min_level:
        warnings.append("Invalid level range: max_level is below min_level.")
        return []

    bands = recommend_bands_from_level_range(min_level, max_level)
    if min_level < _lowest_known_level() or max_level > _highest_known_level():
        warnings.append("Level range extends outside PF2 band levels.")
    if not bands:
        warnings.append("Level range does not overlap any PF2 spawn band.")
    elif len(bands) > 1:
        warnings.append("Level range overlaps multiple PF2 spawn bands.")
    return bands


def _coerce_int(value) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_values(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable):
        return list(value)
    return [value]


def _unique_sorted(values: list[int]) -> list[int]:
    return sorted(set(values))


def _lowest_known_level() -> int:
    return min(definition.min_level for definition in SPAWN_BANDS.values())


def _highest_known_level() -> int:
    return max(definition.max_level for definition in SPAWN_BANDS.values())


def _entry_line(entry: LegacyHuntEntryAudit) -> str:
    species = entry.species_id or "<missing species>"
    return (
        f"{species}: weight {_display_value(entry.original_weight)} -> "
        f"{_display_value(entry.recommended_frequency)}; levels "
        f"{_level_range(entry)} -> bands {_display_list(entry.recommended_bands)}; "
        f"existing frequency {_display_value(entry.existing_frequency)}; "
        f"existing tiers {_display_list(entry.existing_tiers)}"
    )


def _level_range(entry: LegacyHuntEntryAudit) -> str:
    if entry.original_min_level is None or entry.original_max_level is None:
        return "-"
    return f"{entry.original_min_level}-{entry.original_max_level}"


def _display_value(value) -> str:
    return str(value) if value is not None else "-"


def _display_list(values: list[int]) -> str:
    if not values:
        return "-"
    return ", ".join(str(value) for value in values)

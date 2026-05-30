"""Adapters from existing room spawn data to PF2 spawn charts."""

from __future__ import annotations

import ast
import json
import re
from collections.abc import Iterable, Mapping
from typing import Any

from .constants import FREQUENCIES, SpawnFrequency
from .schema import SpawnChart, SpawnEntry
from .selection import validate_spawn_chart


class SpawnAdapterError(ValueError):
    """Raised when existing spawn data cannot be converted safely."""


_FREQUENCY_ALIASES = {
    "f": SpawnFrequency.FREQUENT.value,
    "freq": SpawnFrequency.FREQUENT.value,
    "frequent": SpawnFrequency.FREQUENT.value,
    "c": SpawnFrequency.COMMON.value,
    "common": SpawnFrequency.COMMON.value,
    "u": SpawnFrequency.UNCOMMON.value,
    "uncommon": SpawnFrequency.UNCOMMON.value,
    "r": SpawnFrequency.RARE.value,
    "rare": SpawnFrequency.RARE.value,
    "epic": SpawnFrequency.RARE.value,
    "s": SpawnFrequency.SPECIAL.value,
    "special": SpawnFrequency.SPECIAL.value,
    "legendary": SpawnFrequency.SPECIAL.value,
    "mythical": SpawnFrequency.SPECIAL.value,
}


def _safe_getattr(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    try:
        value = getattr(obj, name)
    except Exception:
        return default
    return default if value is None else value


def _as_values(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable):
        return list(value)
    return [value]


def _normalize_area_key(value: Any) -> str:
    area_key = str(value).strip() if value is not None else ""
    if not area_key:
        raise SpawnAdapterError("Spawn chart area_key must be a non-empty value.")
    return area_key


def _area_key_from_room(room: Any, area_key: Any = None) -> str:
    if area_key is not None:
        return _normalize_area_key(area_key)

    db = _safe_getattr(room, "db")
    for value in (
        _safe_getattr(db, "spawn_area_key"),
        _safe_getattr(room, "key"),
        _safe_getattr(room, "id"),
    ):
        if value is not None and str(value).strip():
            return str(value).strip()

    raise SpawnAdapterError("Could not determine spawn chart area_key from room.")


def normalize_species_id(value: Any) -> str:
    species_id = str(value).strip() if value is not None else ""
    if not species_id:
        raise SpawnAdapterError("Spawn entry species_id must be a non-empty value.")
    return species_id


def normalize_frequency(value: Any) -> str:
    frequency = str(value).strip().lower() if value is not None else SpawnFrequency.COMMON.value
    if not frequency:
        frequency = SpawnFrequency.COMMON.value
    normalized = _FREQUENCY_ALIASES.get(frequency)
    if normalized not in FREQUENCIES:
        raise SpawnAdapterError(f"Unknown spawn frequency: {value!r}.")
    return normalized


def normalize_band(value: Any) -> int:
    if isinstance(value, bool):
        raise SpawnAdapterError(f"Invalid spawn band: {value!r}.")
    if isinstance(value, int):
        band = value
    else:
        text = str(value).strip().lower()
        match = re.fullmatch(r"(?:t|tier|b|band)?\s*([1-4])", text)
        if not match:
            raise SpawnAdapterError(f"Invalid spawn band: {value!r}.")
        band = int(match.group(1))
    if band not in {1, 2, 3, 4}:
        raise SpawnAdapterError(f"Invalid spawn band: {value!r}.")
    return band


def _normalize_enabled(entry: dict[str, Any]) -> bool:
    if "enabled" in entry:
        value = entry["enabled"]
    elif "disabled" in entry:
        value = not _coerce_bool(entry["disabled"])
        return value
    else:
        return True
    return _coerce_bool(value)


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on", "enabled"}:
            return True
        if normalized in {"0", "false", "no", "off", "disabled"}:
            return False
        raise SpawnAdapterError(f"Invalid enabled flag: {value!r}.")
    return bool(value)


def _bands_from_entry(entry: dict[str, Any]) -> list[int]:
    for key in ("bands", "band", "tiers", "tier"):
        if key in entry:
            values = _as_values(entry[key])
            if not values:
                return [1]
            return [normalize_band(value) for value in values]
    return [1]


def coerce_spawn_data_entries(data: Any) -> list[dict[str, Any]]:
    if data is None:
        return []
    if isinstance(data, str):
        data = _parse_stringified_spawn_data(data)
    elif isinstance(data, Mapping):
        raise SpawnAdapterError("Spawn data must be a list of entry dictionaries.")
    elif not isinstance(data, list):
        if isinstance(data, Iterable):
            data = list(data)
        else:
            raise SpawnAdapterError("Spawn data must be a list of entry dictionaries.")
    entries = []
    if not isinstance(data, list):
        raise SpawnAdapterError("Spawn data must be a list of entry dictionaries.")
    for entry in data:
        if isinstance(entry, Mapping):
            entries.append(dict(entry))
            continue
        if not isinstance(entry, dict):
            raise SpawnAdapterError("Spawn data entries must be dictionaries.")
        entries.append(entry)
    return entries


def _parse_stringified_spawn_data(data: str) -> Any:
    text = data.strip()
    if not text:
        return []
    for parser in (json.loads, ast.literal_eval):
        try:
            return parser(text)
        except (ValueError, SyntaxError):
            continue
    raise SpawnAdapterError("Spawn data string must contain a list of entry dictionaries.")


def _spawn_entries_from_data(data: Any) -> list[SpawnEntry]:
    spawn_entries: list[SpawnEntry] = []
    for raw_entry in coerce_spawn_data_entries(data):
        species_id = normalize_species_id(raw_entry.get("species") or raw_entry.get("name"))
        frequency = normalize_frequency(raw_entry.get("frequency", raw_entry.get("rarity")))
        enabled = _normalize_enabled(raw_entry)
        for band in _bands_from_entry(raw_entry):
            spawn_entries.append(
                SpawnEntry(
                    species_id=species_id,
                    frequency=frequency,
                    band=band,
                    enabled=enabled,
                )
            )
    return spawn_entries


def spawn_chart_from_hunt_chart(data: Any, area_key: Any) -> SpawnChart:
    chart = SpawnChart(
        area_key=_normalize_area_key(area_key),
        entries=_spawn_entries_from_data(data),
    )
    return validate_spawn_chart(chart)


def spawn_chart_from_spawn_table(data: Any, area_key: Any) -> SpawnChart:
    chart = SpawnChart(
        area_key=_normalize_area_key(area_key),
        entries=_spawn_entries_from_data(data),
    )
    return validate_spawn_chart(chart)


def spawn_chart_from_room(room: Any, area_key: Any = None) -> SpawnChart:
    resolved_area_key = _area_key_from_room(room, area_key=area_key)
    db = _safe_getattr(room, "db")
    hunt_chart = _safe_getattr(db, "hunt_chart")
    if hunt_chart:
        return spawn_chart_from_hunt_chart(hunt_chart, resolved_area_key)

    spawn_table = _safe_getattr(db, "spawn_table")
    if spawn_table:
        return spawn_chart_from_spawn_table(spawn_table, resolved_area_key)

    chart = SpawnChart(area_key=resolved_area_key, entries=[])
    return validate_spawn_chart(chart)

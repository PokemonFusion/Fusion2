"""File-backed loaders for canonical PF2 spawn profile seed data."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .profiles import (
    AreaSpawnEntry,
    AreaSpawnProfile,
    SpeciesSpawnProfile,
    SpawnProfileError,
    resolve_area_spawn_chart,
    validate_area_spawn_entry,
    validate_area_spawn_profile,
    validate_species_spawn_profile,
)
from .schema import SpawnChart


DATA_DIR = Path(__file__).resolve().parent / "data"
SAMPLE_SPECIES_PROFILES_PATH = DATA_DIR / "species_profiles_sample.json"
SAMPLE_AREA_PROFILES_PATH = DATA_DIR / "area_profiles_sample.json"


class SpawnProfileDataError(SpawnProfileError):
    """Raised when file-backed spawn profile data is malformed."""


def load_species_profiles_from_path(path) -> dict[str, SpeciesSpawnProfile]:
    return load_species_profiles_from_mapping(_load_json_mapping(path))


def load_area_profiles_from_path(path) -> dict[str, AreaSpawnProfile]:
    return load_area_profiles_from_mapping(_load_json_mapping(path))


def load_species_profiles_from_mapping(data: Mapping[str, Any]) -> dict[str, SpeciesSpawnProfile]:
    items = _required_list(data, "profiles", "species profile data")
    profiles: dict[str, SpeciesSpawnProfile] = {}
    for index, raw_profile in enumerate(items, start=1):
        raw_profile = _required_mapping(raw_profile, f"species profile #{index}")
        species_id = _required_text(raw_profile, "species_id", f"species profile #{index}")
        if species_id in profiles:
            raise SpawnProfileDataError(f"Duplicate species profile: {species_id!r}.")
        if "frequencies_by_band" not in raw_profile:
            raise SpawnProfileDataError(f"Missing frequencies_by_band for species {species_id!r}.")
        profile = SpeciesSpawnProfile(
            species_id=species_id,
            enabled=_optional_bool(raw_profile, "enabled", True, f"species profile {species_id!r}"),
            frequencies_by_band=_band_frequency_map(
                raw_profile["frequencies_by_band"],
                f"species profile {species_id!r}",
            ),
        )
        profiles[species_id] = validate_species_spawn_profile(profile)
    return profiles


def load_area_profiles_from_mapping(data: Mapping[str, Any]) -> dict[str, AreaSpawnProfile]:
    items = _required_list(data, "areas", "area profile data")
    profiles: dict[str, AreaSpawnProfile] = {}
    for index, raw_area in enumerate(items, start=1):
        raw_area = _required_mapping(raw_area, f"area profile #{index}")
        area_key = _required_text(raw_area, "area_key", f"area profile #{index}")
        if area_key in profiles:
            raise SpawnProfileDataError(f"Duplicate area profile: {area_key!r}.")
        entries = _area_entries(raw_area, area_key)
        profile = AreaSpawnProfile(area_key=area_key, entries=entries)
        profiles[area_key] = validate_area_spawn_profile(profile)
    return profiles


def resolve_area_from_profile_data(
    area_key: str,
    species_profiles: Mapping[str, SpeciesSpawnProfile],
    area_profiles: Mapping[str, AreaSpawnProfile],
) -> SpawnChart:
    key = str(area_key).strip()
    if not key:
        raise SpawnProfileDataError("area_key must be a non-empty string.")
    try:
        area_profile = area_profiles[key]
    except KeyError as exc:
        raise SpawnProfileDataError(f"Unknown area profile: {key!r}.") from exc
    return resolve_area_spawn_chart(area_profile, species_profiles)


def load_sample_species_profiles() -> dict[str, SpeciesSpawnProfile]:
    return load_species_profiles_from_path(SAMPLE_SPECIES_PROFILES_PATH)


def load_sample_area_profiles() -> dict[str, AreaSpawnProfile]:
    return load_area_profiles_from_path(SAMPLE_AREA_PROFILES_PATH)


def resolve_sample_area(area_key: str) -> SpawnChart:
    return resolve_area_from_profile_data(
        area_key,
        load_sample_species_profiles(),
        load_sample_area_profiles(),
    )


def _load_json_mapping(path) -> dict[str, Any]:
    path = Path(path)
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise SpawnProfileDataError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SpawnProfileDataError(f"Spawn profile file must contain a JSON object: {path}.")
    return data


def _required_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SpawnProfileDataError(f"{label} must be an object.")
    return value


def _required_list(data: Mapping[str, Any], key: str, label: str) -> list[Any]:
    if key not in data:
        raise SpawnProfileDataError(f"Missing {key} in {label}.")
    value = data[key]
    if not isinstance(value, list):
        raise SpawnProfileDataError(f"{key} in {label} must be a list.")
    return value


def _required_text(data: Mapping[str, Any], key: str, label: str) -> str:
    if key not in data:
        raise SpawnProfileDataError(f"Missing {key} in {label}.")
    value = str(data[key]).strip() if data[key] is not None else ""
    if not value:
        raise SpawnProfileDataError(f"{key} in {label} must be a non-empty string.")
    return value


def _optional_bool(data: Mapping[str, Any], key: str, default: bool, label: str) -> bool:
    if key not in data:
        return default
    value = data[key]
    if not isinstance(value, bool):
        raise SpawnProfileDataError(f"{key} in {label} must be a boolean.")
    return value


def _band_frequency_map(raw_map: Any, label: str) -> dict[int, str | None]:
    raw_map = _required_mapping(raw_map, f"{label} frequencies_by_band")
    result: dict[int, str | None] = {}
    for raw_band, frequency in raw_map.items():
        band = _band_key(raw_band, label)
        result[band] = frequency
    return result


def _band_key(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise SpawnProfileDataError(f"Invalid band key in {label}: {value!r}.")
    try:
        band = int(value)
    except (TypeError, ValueError) as exc:
        raise SpawnProfileDataError(f"Invalid band key in {label}: {value!r}.") from exc
    return band


def _area_entries(raw_area: Mapping[str, Any], area_key: str) -> list[AreaSpawnEntry]:
    raw_entries = _required_list(raw_area, "entries", f"area profile {area_key!r}")
    entries: list[AreaSpawnEntry] = []
    seen_species: set[str] = set()
    for index, raw_entry in enumerate(raw_entries, start=1):
        raw_entry = _required_mapping(raw_entry, f"area {area_key!r} entry #{index}")
        species_id = _required_text(raw_entry, "species_id", f"area {area_key!r} entry #{index}")
        if species_id in seen_species:
            raise SpawnProfileDataError(f"Duplicate species {species_id!r} in area {area_key!r}.")
        seen_species.add(species_id)
        overrides = raw_entry.get("frequency_overrides_by_band", {})
        entry = AreaSpawnEntry(
            species_id=species_id,
            enabled=_optional_bool(raw_entry, "enabled", True, f"area {area_key!r} species {species_id!r}"),
            frequency_overrides_by_band=_band_frequency_map(
                overrides,
                f"area {area_key!r} species {species_id!r}",
            ),
        )
        entries.append(validate_area_spawn_entry(entry))
    return entries

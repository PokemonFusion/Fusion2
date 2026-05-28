"""Global species spawn profiles with area-level enablement and overrides."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Optional

from .constants import FREQUENCIES, SPAWN_BANDS
from .schema import SpawnChart, SpawnEntry
from .selection import validate_spawn_chart


class SpawnProfileError(ValueError):
    """Raised when spawn profile data cannot be resolved safely."""


@dataclass(frozen=True)
class SpeciesSpawnProfile:
    species_id: str
    frequencies_by_band: dict[int, str | None]
    enabled: bool = True


@dataclass(frozen=True)
class AreaSpawnEntry:
    species_id: str
    enabled: bool = True
    frequency_overrides_by_band: dict[int, str | None] = field(default_factory=dict)


@dataclass(frozen=True)
class AreaSpawnProfile:
    area_key: str
    entries: list[AreaSpawnEntry]


def validate_species_spawn_profile(profile: SpeciesSpawnProfile) -> SpeciesSpawnProfile:
    if not isinstance(profile, SpeciesSpawnProfile):
        raise TypeError("Species spawn profile must be a SpeciesSpawnProfile.")
    _normalize_species_id(profile.species_id)
    _validate_frequency_map(profile.frequencies_by_band, "species profile frequencies")
    if not isinstance(profile.enabled, bool):
        raise SpawnProfileError("Species spawn profile enabled must be a boolean.")
    return profile


def validate_area_spawn_entry(entry: AreaSpawnEntry) -> AreaSpawnEntry:
    if not isinstance(entry, AreaSpawnEntry):
        raise TypeError("Area spawn entry must be an AreaSpawnEntry.")
    _normalize_species_id(entry.species_id)
    if not isinstance(entry.enabled, bool):
        raise SpawnProfileError("Area spawn entry enabled must be a boolean.")
    _validate_frequency_map(entry.frequency_overrides_by_band, "area frequency overrides")
    return entry


def validate_area_spawn_profile(profile: AreaSpawnProfile) -> AreaSpawnProfile:
    if not isinstance(profile, AreaSpawnProfile):
        raise TypeError("Area spawn profile must be an AreaSpawnProfile.")
    if not isinstance(profile.area_key, str) or not profile.area_key.strip():
        raise SpawnProfileError("Area spawn profile area_key must be a non-empty string.")
    if not isinstance(profile.entries, list):
        raise SpawnProfileError("Area spawn profile entries must be a list.")
    for entry in profile.entries:
        validate_area_spawn_entry(entry)
    return profile


def resolve_area_spawn_chart(
    area_profile: AreaSpawnProfile,
    species_profiles: Mapping[str, SpeciesSpawnProfile] | Iterable[SpeciesSpawnProfile],
) -> SpawnChart:
    validate_area_spawn_profile(area_profile)
    profile_map = _species_profile_map(species_profiles)
    entries: list[SpawnEntry] = []

    for area_entry in area_profile.entries:
        if not area_entry.enabled:
            continue
        species_id = _normalize_species_id(area_entry.species_id)
        species_profile = profile_map.get(species_id)
        if species_profile is not None and not species_profile.enabled:
            continue

        for band in SPAWN_BANDS:
            frequency = _resolve_frequency(area_entry, species_profile, band)
            if frequency is None:
                continue
            entries.append(
                SpawnEntry(
                    species_id=species_id,
                    frequency=frequency,
                    band=band,
                    enabled=True,
                )
            )

    chart = SpawnChart(area_key=area_profile.area_key.strip(), entries=entries)
    return validate_spawn_chart(chart)


def _species_profile_map(
    species_profiles: Mapping[str, SpeciesSpawnProfile] | Iterable[SpeciesSpawnProfile],
) -> dict[str, SpeciesSpawnProfile]:
    if isinstance(species_profiles, Mapping):
        profiles = species_profiles.values()
    else:
        profiles = species_profiles

    result: dict[str, SpeciesSpawnProfile] = {}
    for profile in profiles:
        validate_species_spawn_profile(profile)
        species_id = _normalize_species_id(profile.species_id)
        result[species_id] = profile
    return result


def _resolve_frequency(
    area_entry: AreaSpawnEntry,
    species_profile: Optional[SpeciesSpawnProfile],
    band: int,
) -> str | None:
    if band in area_entry.frequency_overrides_by_band:
        override = _normalize_frequency(
            area_entry.frequency_overrides_by_band[band],
            f"area override for band {band}",
        )
        if override is not None:
            return override

    if species_profile is None:
        return None
    return _normalize_frequency(
        species_profile.frequencies_by_band.get(band),
        f"species profile frequency for band {band}",
    )


def _validate_frequency_map(value: dict[int, str | None], label: str) -> None:
    if not isinstance(value, dict):
        raise SpawnProfileError(f"{label} must be a dict.")
    for band, frequency in value.items():
        _normalize_band(band)
        _normalize_frequency(frequency, f"{label} band {band}")


def _normalize_species_id(value: str) -> str:
    species_id = str(value).strip() if value is not None else ""
    if not species_id:
        raise SpawnProfileError("species_id must be a non-empty string.")
    return species_id


def _normalize_band(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SpawnProfileError(f"Invalid spawn band: {value!r}.")
    if value not in SPAWN_BANDS:
        raise SpawnProfileError(f"Invalid spawn band: {value!r}.")
    return value


def _normalize_frequency(value: str | None, label: str) -> str | None:
    if value is None:
        return None
    frequency = str(value).strip().lower()
    if not frequency:
        return None
    if frequency not in FREQUENCIES:
        raise SpawnProfileError(f"Invalid spawn frequency for {label}: {value!r}.")
    return frequency

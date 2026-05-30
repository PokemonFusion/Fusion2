"""Audit helpers for canonical PF2 area profile resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .constants import SPAWN_BANDS, SpawnFrequency
from .preview import format_species_group
from .profile_data import SpawnProfileDataError, load_sample_area_profiles, load_sample_species_profiles
from .profiles import (
    AreaSpawnProfile,
    SpeciesSpawnProfile,
    resolve_area_spawn_chart,
    validate_area_spawn_profile,
    validate_species_spawn_profile,
)


PROFILE_COMPARE_SOURCE = "profile sample data"


@dataclass(frozen=True)
class ProfileSpawnComparison:
    area_key: str
    area_entry_count: int
    resolved_entry_count: int
    resolved_species: tuple[str, ...]
    global_default_species: tuple[str, ...]
    override_species: tuple[str, ...]
    unresolved_species: tuple[str, ...]
    disabled_species: tuple[str, ...]
    special_species: tuple[str, ...]


def compare_sample_profile_area(area_key: str) -> ProfileSpawnComparison:
    return compare_profile_area(
        area_key,
        load_sample_species_profiles(),
        load_sample_area_profiles(),
    )


def compare_profile_area(
    area_key: str,
    species_profiles: Mapping[str, SpeciesSpawnProfile],
    area_profiles: Mapping[str, AreaSpawnProfile],
) -> ProfileSpawnComparison:
    key = str(area_key).strip()
    if not key:
        raise SpawnProfileDataError("area_key must be a non-empty string.")
    try:
        area_profile = area_profiles[key]
    except KeyError as exc:
        raise SpawnProfileDataError(f"Unknown area profile: {key!r}.") from exc

    validate_area_spawn_profile(area_profile)
    for species_profile in species_profiles.values():
        validate_species_spawn_profile(species_profile)

    chart = resolve_area_spawn_chart(area_profile, species_profiles)
    resolved_index = _resolved_index(chart.entries)
    resolved_species = set(resolved_index)
    global_default_species: set[str] = set()
    override_species: set[str] = set()
    unresolved_species: set[str] = set()
    disabled_species: set[str] = set()

    for area_entry in area_profile.entries:
        species_id = area_entry.species_id
        if not area_entry.enabled:
            disabled_species.add(species_id)
            continue
        if species_id not in resolved_species:
            unresolved_species.add(species_id)
            continue
        profile = species_profiles.get(species_id)
        for band in SPAWN_BANDS:
            if band not in resolved_index[species_id]:
                continue
            if _has_real_override(area_entry.frequency_overrides_by_band.get(band)):
                override_species.add(species_id)
            elif profile and _has_real_frequency(profile.frequencies_by_band.get(band)):
                global_default_species.add(species_id)

    special_species = {
        species_id
        for species_id, frequencies_by_band in resolved_index.items()
        if any(frequency == SpawnFrequency.SPECIAL.value for frequency in frequencies_by_band.values())
    }

    return ProfileSpawnComparison(
        area_key=area_profile.area_key,
        area_entry_count=len(area_profile.entries),
        resolved_entry_count=len(chart.entries),
        resolved_species=tuple(sorted(resolved_species)),
        global_default_species=tuple(sorted(global_default_species)),
        override_species=tuple(sorted(override_species)),
        unresolved_species=tuple(sorted(unresolved_species)),
        disabled_species=tuple(sorted(disabled_species)),
        special_species=tuple(sorted(special_species)),
    )


def format_profile_spawn_comparison(comparison: ProfileSpawnComparison, limit: int = 12) -> str:
    return "\n".join(
        [
            "PF2 Spawn Profile Compare",
            f"Area key: {comparison.area_key}",
            f"Source: {PROFILE_COMPARE_SOURCE}",
            f"Area entries: {comparison.area_entry_count}",
            f"Resolved SpawnChart entries: {comparison.resolved_entry_count}",
            f"Resolved species: {format_species_group(comparison.resolved_species, limit)}",
            f"Global defaults: {format_species_group(comparison.global_default_species, limit)}",
            f"Area overrides: {format_species_group(comparison.override_species, limit)}",
            f"Enabled unresolved: {format_species_group(comparison.unresolved_species, limit)}",
            f"Disabled ignored: {format_species_group(comparison.disabled_species, limit)}",
            f"Special configured: {format_species_group(comparison.special_species, limit)}",
            "Special entries are configured separately from normal roll tests.",
        ]
    )


def _resolved_index(entries):
    index: dict[str, dict[int, str]] = {}
    for entry in entries:
        index.setdefault(entry.species_id, {})[entry.band] = entry.frequency
    return index


def _has_real_override(value: str | None) -> bool:
    return value is not None and bool(str(value).strip())


def _has_real_frequency(value: str | None) -> bool:
    return value is not None and bool(str(value).strip())

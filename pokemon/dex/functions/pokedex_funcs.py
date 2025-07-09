"""Helper functions for pokedex data."""

from typing import List, Tuple

from ...data.regiondex import REGION_POKEDEX
from ..catch_rates import CATCH_INFO


def get_region_entries(region: str) -> List[Tuple[int, str]]:
    """Return ``(number, species)`` pairs for a region."""
    key = region.lower()
    if key not in REGION_POKEDEX:
        raise KeyError(f"Unknown region: {region}")
    return REGION_POKEDEX[key]


def get_region_species(region: str) -> List[str]:
    """Return species names in the given regional Pok\xe9dex."""
    return [name for _, name in get_region_entries(region)]


def get_catch_info(species: str):
    """Return catch-related info for the given species.

    Parameters
    ----------
    species: str
        The Pok\xe9mon species name exactly as defined in ``pokedex``.
    """
    return CATCH_INFO.get(species)


def get_catch_rate(species: str) -> int:
    """Return the catch rate for a species or ``0`` if unknown."""
    info = get_catch_info(species)
    return info.get("catchRate", 0) if info else 0


def get_national_entries() -> List[Tuple[int, str]]:
    """Return ``(number, species)`` pairs for the National Pok\xe9dex."""
    from .. import POKEDEX

    entries: List[Tuple[int, str]] = []
    for name, details in POKEDEX.items():
        num = getattr(details, "num", None)
        if num is None and isinstance(details, dict):
            num = details.get("num")
        if num:
            entries.append((int(num), name.lower()))
    entries.sort(key=lambda x: x[0])
    return entries



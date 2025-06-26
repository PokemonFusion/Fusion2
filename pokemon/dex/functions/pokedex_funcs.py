"""Helper functions for pokedex data."""

from typing import List, Tuple

from ...data.regiondex import REGION_POKEDEX


def get_region_entries(region: str) -> List[Tuple[int, str]]:
    """Return ``(number, species)`` pairs for a region."""
    key = region.lower()
    if key not in REGION_POKEDEX:
        raise KeyError(f"Unknown region: {region}")
    return REGION_POKEDEX[key]


def get_region_species(region: str) -> List[str]:
    """Return species names in the given regional Pok\xe9dex."""
    return [name for _, name in get_region_entries(region)]

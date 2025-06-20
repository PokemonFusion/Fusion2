"""Helpers for determining valid starter Pokémon."""

from typing import List, Tuple

from pokemon.dex import POKEDEX

EXCLUDED_TAGS = {"Sub-Legendary", "Mythical"}


def _build_starters() -> List[Tuple[int, str]]:
    """Generate a sorted list of (num, name) tuples for valid starters."""
    starters: List[Tuple[int, str]] = []
    for name, mon in POKEDEX.items():
        num = getattr(mon, "num", 0)
        if num <= 0:
            continue
        if getattr(mon, "prevo", None):
            continue
        tags = []
        raw = getattr(mon, "raw", {})
        if isinstance(raw, dict):
            tags = raw.get("tags", [])
        if any(tag in EXCLUDED_TAGS for tag in tags):
            continue
        starters.append((num, name))
    starters.sort(key=lambda t: t[0])
    return starters


STARTER_ENTRIES: List[Tuple[int, str]] = _build_starters()


def get_starter_numbers() -> List[int]:
    """Return the National Dex numbers for all valid starter Pokémon."""
    return [num for num, _ in STARTER_ENTRIES]


STARTER_NUMBERS: List[int] = get_starter_numbers()


def get_starter_names() -> List[str]:
    """Return the valid starter Pokémon names."""
    return [name for _, name in STARTER_ENTRIES]



"""Helpers for determining valid starter Pokémon."""

from typing import Dict, List, Tuple

from pokemon.dex import POKEDEX

EXCLUDED_TAGS = {"Sub-Legendary", "Mythical"}


def _build_starters() -> Tuple[List[Tuple[int, str]], Dict[str, str]]:
    """Generate a sorted list of (num, name) tuples for valid starters.

    Returns
    -------
    Tuple[List[Tuple[int, str]], Dict[str, str]]
        A list of ``(num, display_name)`` pairs and a mapping of valid input
        strings to the canonical Pokedex key.
    """

    starters: List[Tuple[int, str]] = []
    lookup: Dict[str, str] = {}
    for key, mon in POKEDEX.items():
        num = getattr(mon, "num", 0)
        if num <= 0:
            continue
        if getattr(mon, "prevo", None):
            continue
        raw = getattr(mon, "raw", {}) or {}
        tags = raw.get("tags", []) if isinstance(raw, dict) else []
        forme = raw.get("forme") if isinstance(raw, dict) else None
        if any(tag in EXCLUDED_TAGS for tag in tags):
            continue
        if forme and forme not in ("Alola", "Galar"):
            continue
        display_name = getattr(mon, "name", key)
        starters.append((num, display_name))
        lookup[display_name.lower()] = key
        lookup[key.lower()] = key
    starters.sort(key=lambda t: t[0])
    return starters, lookup


STARTER_ENTRIES, STARTER_LOOKUP = _build_starters()


def get_starter_numbers() -> List[int]:
    """Return the National Dex numbers for all valid starter Pokémon."""
    return [num for num, _ in STARTER_ENTRIES]


STARTER_NUMBERS: List[int] = get_starter_numbers()


def get_starter_names() -> List[str]:
    """Return the valid starter Pokémon names."""
    return [name for _, name in STARTER_ENTRIES]



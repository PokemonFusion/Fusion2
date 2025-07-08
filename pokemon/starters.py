"""Helpers for determining valid starter Pokémon."""

from typing import Dict, List, Tuple
from pokemon.dex import POKEDEX

# Forms or categories we explicitly exclude from “starter” status
EXCLUDED_TAGS = {"Sub-Legendary", "Mythical", 'Restricted Legendary'}


def _build_starters() -> Tuple[
    List[Tuple[int, str]],
    Dict[str, str],
    Dict[str, str],
]:
    """
    Generate:
      1) A sorted list of (num, display_name) tuples for valid starters,
      2) A lookup of valid input strings -> canonical dex key,
      3) A mapping of dex key -> display_name for UI use.
    """
    starters: List[Tuple[int, str]] = []
    lookup: Dict[str, str] = {}
    display_map: Dict[str, str] = {}

    for key, mon in POKEDEX.items():
        # Numeric dex number
        num = mon.num
        if num <= 0:
            continue
        # Only base forms (no evolutions)
        if mon.prevo:
            continue

        # Pull tags/forms out of the raw dict
        raw = mon.raw or {}
        tags = raw.get("tags", [])
        forme = raw.get("forme")

        # Exclude Mythicals/Legendaries and non-starter special forms
        if any(tag in EXCLUDED_TAGS for tag in tags):
            continue
        if forme and forme not in ("Alola", "Galar"):
            continue

        # **Key change**: grab the display name from raw["name"]
        display_name = raw.get("name", mon.name)
        starters.append((num, display_name))

        # Allow lookup by either the display name or the raw key
        lookup[display_name.lower()] = key
        lookup[key.lower()] = key

        # Map dex-key → display name for UI
        display_map[key] = display_name

    # Sort in ascending National Dex order
    starters.sort(key=lambda t: t[0])
    return starters, lookup, display_map


# Build once at import time
STARTER_ENTRIES, STARTER_LOOKUP, STARTER_DISPLAY_MAP = _build_starters()


def get_starter_numbers() -> List[int]:
    """Return the National Dex numbers for all valid starter Pokémon."""
    return [num for num, _ in STARTER_ENTRIES]


STARTER_NUMBERS: List[int] = get_starter_numbers()


def get_starter_names() -> List[str]:
    """Return the valid starter Pokémon **display** names, in dex order."""
    return [name for _, name in STARTER_ENTRIES]


def get_starter_display_map() -> Dict[str, str]:
    """Return a mapping of dex_key → display_name for all valid starters."""
    return STARTER_DISPLAY_MAP

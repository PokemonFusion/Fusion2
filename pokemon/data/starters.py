"""Helpers for determining valid starter Pokémon."""

from typing import Dict, List, Tuple

from ..dex import POKEDEX

# Forms or categories we explicitly exclude from “starter” status
EXCLUDED_TAGS = {
    "Sub-Legendary",
    "Mythical",
    "Restricted Legendary",
    "Ultra Beast",
    "Paradox",
}

ULTRA_BEAST_EXCLUSIONS = {
    "Nihilego",
    "Buzzwole",
    "Pheromosa",
    "Xurkitree",
    "Celesteela",
    "Kartana",
    "Guzzlord",
    "Poipole",
    "Stakataka",
    "Blacephalon",
}

PARADOX_EXCLUSIONS = {
    "Great Tusk",
    "Scream Tail",
    "Brute Bonnet",
    "Flutter Mane",
    "Slither Wing",
    "Sandy Shocks",
    "Iron Treads",
    "Iron Bundle",
    "Iron Hands",
    "Iron Jugulis",
    "Iron Moth",
    "Iron Thorns",
    "Roaring Moon",
    "Iron Valiant",
    "Walking Wake",
    "Iron Leaves",
    "Gouging Fire",
    "Raging Bolt",
    "Iron Boulder",
    "Iron Crown",
}

HARD_EXCLUDED_STARTERS = ULTRA_BEAST_EXCLUSIONS | PARADOX_EXCLUSIONS

# Reserved for future design decisions around static/gift/special Pokemon such
# as fossils, Rotom, Porygon, and Gimmighoul. Intentionally not active.
SPECIAL_RARE_STARTER_EXCLUSIONS: set[str] = set()

# Regional forms that are considered for starter eligibility
REGIONAL_FORMS = ("Alola", "Galar")


def _normalize_starter_key(value: object) -> str:
    return str(value or "").replace(" ", "").replace("-", "").replace("'", "").lower()


HARD_EXCLUDED_STARTER_KEYS = {
    _normalize_starter_key(species) for species in HARD_EXCLUDED_STARTERS
}


def _has_excluded_tag(tags: list[str]) -> bool:
    return any(tag in EXCLUDED_TAGS for tag in tags)


def _is_hard_excluded_species(species_key: str, mon_obj) -> bool:
    raw = mon_obj.raw or {}
    display_name = raw.get("name", mon_obj.name)
    return (
        _normalize_starter_key(species_key) in HARD_EXCLUDED_STARTER_KEYS
        or _normalize_starter_key(display_name) in HARD_EXCLUDED_STARTER_KEYS
    )


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
    key_lookup: Dict[str, str] = {}

    for k, mon in POKEDEX.items():
        key_lookup[k.lower()] = k
        key_lookup[(mon.raw or {}).get("name", mon.name).lower()] = k

    def add_entry(k: str, mon_obj) -> None:
        disp = (mon_obj.raw or {}).get("name", mon_obj.name)
        num = mon_obj.num
        if (num, disp) not in starters:
            starters.append((num, disp))
        lookup[disp.lower()] = k
        lookup[k.lower()] = k
        display_map[k] = disp

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

        # Exclude Mythicals/Legendaries and known legendary-adjacent groups.
        if _has_excluded_tag(tags):
            continue
        if forme and forme not in REGIONAL_FORMS:
            continue
        if _is_hard_excluded_species(key, mon):
            continue

        add_entry(key, mon)

        if mon.is_baby and mon.evos:
            for evo in mon.evos:
                ekey = key_lookup.get(evo.lower())
                if not ekey:
                    continue
                evo_mon = POKEDEX.get(ekey)
                if not evo_mon:
                    continue
                raw2 = evo_mon.raw or {}
                tags2 = raw2.get("tags", [])
                forme2 = raw2.get("forme")
                if _has_excluded_tag(tags2):
                    continue
                if forme2 and forme2 not in REGIONAL_FORMS:
                    continue
                if _is_hard_excluded_species(ekey, evo_mon):
                    continue
                add_entry(ekey, evo_mon)

    # Sort in ascending National Dex order
    starters.sort(key=lambda t: t[0])
    return starters, lookup, display_map


# Build once at import time
STARTER_ENTRIES, STARTER_LOOKUP, STARTER_DISPLAY_MAP = _build_starters()


def get_starter_numbers() -> List[int]:
    """Return the National Dex numbers for all valid starter Pokémon."""
    return [num for num, _ in STARTER_ENTRIES]


STARTER_NUMBERS: List[int] = get_starter_numbers()


def resolve_starter_key(species_name: str) -> str | None:
    """Return the canonical dex key for a valid starter input."""
    entry = (species_name or "").strip().lower()
    if not entry:
        return None
    return STARTER_LOOKUP.get(entry)


def is_valid_starter_key(species_key: str) -> bool:
    """Return ``True`` if ``species_key`` is in the generated starter set."""
    return species_key in STARTER_DISPLAY_MAP


def get_starter_names() -> List[str]:
    """Return the valid starter Pokémon **display** names, in dex order."""
    return [name for _, name in STARTER_ENTRIES]


def get_starter_display_map() -> Dict[str, str]:
    """Return a mapping of dex_key → display_name for all valid starters."""
    return STARTER_DISPLAY_MAP

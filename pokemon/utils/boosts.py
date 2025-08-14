"""Shared helpers for stat mappings and temporary boosts.

This module provides a minimal set of utilities that are used by both the
battle engine and the dex move/ability callbacks.  Importing from here keeps
higher-level modules decoupled and avoids circular imports between the battle
and dex packages.
"""

from typing import Dict

# Mapping of shorthand stat names to their canonical attribute names.
STAT_KEY_MAP = {
    "hp": "hp",
    "atk": "attack",
    "def": "defense",
    "spa": "special_attack",
    "spd": "special_defense",
    "spe": "speed",
}

REVERSE_STAT_KEY_MAP = {v: k for k, v in STAT_KEY_MAP.items()}
ALL_STATS = list(STAT_KEY_MAP.values())


def apply_boost(pokemon, boosts: Dict[str, int]) -> None:
    """Apply stat stage changes to ``pokemon``.

    The provided ``boosts`` mapping uses short stat identifiers (e.g.
    ``"atk"``, ``"spe"``).  Existing boosts are normalised using
    :data:`STAT_KEY_MAP` and each stage change is clamped between -6 and 6.
    """

    current = getattr(pokemon, "boosts", {}) or {}
    if not isinstance(current, dict):  # pragma: no cover - defensive
        current = {}

    # normalise existing keys
    current = {STAT_KEY_MAP.get(k, k): v for k, v in current.items()}

    for stat, amount in boosts.items():
        full = STAT_KEY_MAP.get(stat, stat)
        cur = current.get(full, 0)
        current[full] = max(-6, min(6, cur + amount))

    pokemon.boosts = current


__all__ = ["STAT_KEY_MAP", "REVERSE_STAT_KEY_MAP", "ALL_STATS", "apply_boost"]

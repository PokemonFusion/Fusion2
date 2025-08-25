from __future__ import annotations

"""Utility helpers for world building."""

from typing import Dict, Optional

# Unified reverse-direction map. Extend as needed.
REVERSE_DIRS: Dict[str, str] = {
    "north": "south", "south": "north",
    "east": "west", "west": "east",
    "northeast": "southwest", "southwest": "northeast",
    "northwest": "southeast", "southeast": "northwest",
    "up": "down", "down": "up",
    "in": "out", "out": "in",
    "ne": "sw", "sw": "ne", "nw": "se", "se": "nw",
    "n": "s", "s": "n", "e": "w", "w": "e",
}

def reverse_dir(name: str) -> Optional[str]:
    """Return opposite direction for a known direction key."""
    if not name:
        return None
    lc = name.lower()
    rev = REVERSE_DIRS.get(lc)
    if not rev:
        return None
    # preserve original case style roughly
    return (
        rev
        if name.islower()
        else rev.capitalize() if name.istitle() else rev.upper() if name.isupper() else rev
    )

def normalize_aliases(raw: str) -> list[str]:
    """Split comma-separated aliases into a clean list."""
    if not raw:
        return []
    return [a.strip() for a in raw.split(",") if a.strip()]


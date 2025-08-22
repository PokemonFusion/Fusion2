"""Shared battle utilities used across modules."""
from __future__ import annotations

import re


def _normalize_key(name: str) -> str:
    """Return a normalized key for move lookups in ``MOVEDEX``.

    The helper strips non-alphanumeric characters and lowercases the string so
    that move names like ``'10,000,000 Volt Thunderbolt'`` become
    ``'10000000voltthunderbolt'``.  Keeping this function lightweight avoids
    circular imports between :mod:`engine` and :mod:`turnorder`.
    """
    if not name:
        return ""
    return re.sub(r"[^a-z0-9]", "", str(name).lower())

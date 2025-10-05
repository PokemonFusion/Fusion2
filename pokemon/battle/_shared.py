"""Shared battle utilities used across modules."""
from __future__ import annotations

import re
from typing import Any, Iterable, MutableMapping


_NORMALIZED_DEX_IDS: set[int] = set()


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


def ensure_movedex_aliases(movedex: MutableMapping[str, Any]) -> None:
    """Add normalized-key aliases to ``MOVEDEX`` style mappings.

    The Showdown data commonly stores moves using Title Case keys (``"Acid"``)
    while the battle engine normalizes move identifiers (``"acid"``).  To keep
    call sites lightweight, we add aliases the first time a module touches
    ``MOVEDEX`` so lookups succeed regardless of capitalization or punctuation.
    ``movedex`` may be any mutable mapping that exposes ``items`` and
    ``__setitem__``; failures are silently ignored so tests with stub objects
    continue to run.
    """

    mapping_id = id(movedex)
    if mapping_id in _NORMALIZED_DEX_IDS:
        return

    try:
        items: Iterable[tuple[str, Any]] = list(movedex.items())
    except Exception:
        return

    for key, entry in items:
        alias_source = getattr(entry, "id", None) or getattr(entry, "name", None) or key
        normalized = _normalize_key(alias_source)
        if not normalized or normalized in movedex:
            continue
        try:
            movedex[normalized] = entry
        except Exception:
            # If the mapping is immutable or otherwise rejects assignment we
            # stop early to avoid repeated failures.
            return

    _NORMALIZED_DEX_IDS.add(mapping_id)

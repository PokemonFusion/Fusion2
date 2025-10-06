"""Shared battle utilities used across modules."""
from __future__ import annotations

import re
from typing import Any, Iterable, Mapping, MutableMapping


_NORMALIZED_DEX_IDS: dict[int, dict[str, int]] = {}


def _normalize_key(name: str) -> str:
    """Return a normalized MOVEDEX key in TitleKey form.

    Rules
    -----
    - Remove non-alphanumeric characters.
    - Lowercase the remaining characters.
    - Uppercase the *first alphabetical* character only, leaving the rest
      lowercase.  This keeps inputs such as ``"Ancient Power"`` aligned with
      Showdown's ``"Ancientpower"`` keys while retaining numeric prefixes like
      ``"10,000,000 Volt Thunderbolt"`` -> ``"10000000Voltthunderbolt"``.
    """

    cleaned = re.sub(r"[^A-Za-z0-9]", "", str(name or ""))
    if not cleaned:
        return ""

    lowered = cleaned.lower()
    for idx, ch in enumerate(lowered):
        if ch.isalpha():
            return lowered[:idx] + ch.upper() + lowered[idx + 1 :]
    return lowered


def get_raw(entry: Any) -> dict[str, Any]:
    """Return a dictionary copy of a dex entry's raw data."""

    if entry is None:
        return {}

    raw = getattr(entry, "raw", None)
    if isinstance(raw, dict):
        return dict(raw)

    if isinstance(entry, Mapping):
        return dict(entry)

    return {}


def ensure_movedex_aliases(movedex: MutableMapping[str, Any]) -> None:
    """Add TitleKey aliases to ``MOVEDEX`` style mappings."""

    try:
        items: Iterable[tuple[str, Any]] = list(movedex.items())
    except Exception:
        return

    mapping_id = id(movedex)
    state = _NORMALIZED_DEX_IDS.setdefault(mapping_id, {})

    for key, entry in items:
        alias_source = (
            getattr(entry, "id", None)
            or getattr(entry, "name", None)
            or (entry.get("id") if isinstance(entry, Mapping) else None)
            or (entry.get("name") if isinstance(entry, Mapping) else None)
            or key
        )
        normalized = _normalize_key(alias_source)
        if not normalized or key == normalized:
            continue
        entry_id = id(entry)
        stored_id = state.get(normalized)
        existing = movedex.get(normalized)
        if stored_id == entry_id and existing is entry:
            continue
        if stored_id == entry_id and existing is not entry:
            continue
        try:
            movedex[normalized] = entry
        except Exception:
            # If the mapping is immutable or otherwise rejects assignment we
            # stop early to avoid repeated failures.
            return
        state[normalized] = entry_id

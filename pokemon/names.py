"""Compare dex names without changing their stored or displayed spelling."""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable, Mapping
from typing import Any


def normalize_name(value: object) -> str:
    """Ignore spacing, punctuation and accents while retaining gender suffixes."""
    text = str(value or "").replace("♀", "f").replace("♂", "m")
    text = unicodedata.normalize("NFKD", text).casefold()
    return "".join(character for character in text if character.isalnum())


def find_named(items: Iterable, name: object) -> Any | None:
    """Find an existing named object or string by its normalized spelling."""
    key = normalize_name(name)
    if not key:
        return None
    return next((item for item in items if normalize_name(getattr(item, "name", item)) == key), None)


def resolve_dex_entry(dex: Mapping, name: object) -> Any | None:
    """Resolve a dex key or display name in object-backed or dictionary dexes."""
    text = str(getattr(name, "name", name) or "").strip()
    key = normalize_name(text)
    if not key:
        return None
    for candidate in (text, key, key.capitalize()):
        entry = dex.get(candidate)
        if entry is not None:
            return entry
    for dex_key, entry in dex.items():
        display = entry.get("name", dex_key) if isinstance(entry, Mapping) else getattr(entry, "name", dex_key)
        if key in (normalize_name(dex_key), normalize_name(display)):
            return entry
    return None

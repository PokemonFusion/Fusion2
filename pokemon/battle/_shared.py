"""Shared battle utilities used across modules."""

from __future__ import annotations

import re
import sys
from typing import Any, Iterable, Mapping, MutableMapping, Optional

_NORMALIZED_DEX_IDS: dict[int, dict[str, int]] = {}


def weather_suppressed(battle: Any) -> bool:
    """Derive weather suppression from current living active ability holders."""
    participants = getattr(battle, "participants", None)
    if participants is None:
        return bool(getattr(battle, "suppressWeather", False))
    try:
        from pokemon.dex import ABILITYDEX
    except ImportError:  # Minimal battle adapters may omit the optional dex.
        ABILITYDEX = {}

    for part in participants:
        for pokemon in getattr(part, "active", []) or []:
            if getattr(pokemon, "hp", 0) <= 0 or "gastroacid" in getattr(pokemon, "volatiles", {}):
                continue
            ability = getattr(pokemon, "ability", None)
            if isinstance(ability, str):
                ability = ABILITYDEX.get(_normalize_key(ability)) or ABILITYDEX.get(ability)
            raw = getattr(ability, "raw", {}) or {}
            if raw.get("suppressWeather") or getattr(ability, "suppressWeather", False):
                return True
    return False


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


def detached_mapping(value: Any) -> dict[str, Any]:
    """Return ``value`` as a plain dict detached from persistence wrappers."""

    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    try:
        return dict(value)
    except (TypeError, ValueError):
        return {}


def snapshot_battle_value(value: Any) -> Any:
    """Serialize battler and field references without copying live ORM graphs."""
    from .battledata import Field, Move, Pokemon

    # Evennia treats unknown iterable subclasses as saved lists. SpeciesName
    # is a str subclass, so detach it before it enters an Attribute checkpoint.
    if isinstance(value, str):
        return str(value)
    if isinstance(value, Field):
        return {"__pf2_field_ref__": True}
    if isinstance(value, Pokemon):
        reference = value.model_id or f"{value.name}|{value.level}|{value.max_hp}"
        return {"__pf2_pokemon_ref__": reference}
    battle_move = getattr(sys.modules.get("pokemon.battle.engine"), "BattleMove", Move)
    if not isinstance(battle_move, type):
        battle_move = Move
    if isinstance(value, (Move, battle_move)):
        return {"__pf2_move_ref__": value.name, "key": getattr(value, "key", None), "pp": getattr(value, "pp", None)}
    if isinstance(value, Mapping):
        return {key: snapshot_battle_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        items = [snapshot_battle_value(item) for item in value]
        return tuple(items) if isinstance(value, tuple) else items
    return value


def restore_battle_value(value: Any, pokemon_by_ref: Mapping[str, Any], *, field=None) -> Any:
    """Reconnect saved source/target references to the restored roster and field."""
    if isinstance(value, Mapping):
        if set(value) == {"__pf2_field_ref__"}:
            return field
        if set(value) == {"__pf2_pokemon_ref__"}:
            return pokemon_by_ref.get(value["__pf2_pokemon_ref__"])
        if "__pf2_move_ref__" in value:
            from .engine import MOVEDEX, BattleMove

            name = value["__pf2_move_ref__"]
            key = value.get("key") or _normalize_key(name)
            raw = get_raw(MOVEDEX.get(_normalize_key(key)))
            return BattleMove(name, key=key, pp=value.get("pp"), raw=raw,
                              power=raw.get("basePower", 0) or 0, type=raw.get("type"),
                              accuracy=raw.get("accuracy", 100), priority=raw.get("priority", 0))
        return {key: restore_battle_value(item, pokemon_by_ref, field=field) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        items = [restore_battle_value(item, pokemon_by_ref, field=field) for item in value]
        return tuple(items) if isinstance(value, tuple) else items
    return value


def reset_tempvals(pokemon: Any) -> None:
    """Clear turn flags while retaining explicitly scoped entry state."""

    if hasattr(pokemon, "tempvals"):
        previous = getattr(pokemon, "tempvals", {}) or {}
        retained = {key: value for key, value in previous.items()
                    if key in {"moves_used_since_entry", "stat_overrides", "entry_action_turn", "copy_state", "native_form", "sleep_turns", "slp_turns"}}
        setattr(pokemon, "tempvals", retained)


def get_pp(entry: Any) -> Optional[int]:
    """Return the PP value associated with a dex entry if available."""

    if entry is None:
        return None

    value = getattr(entry, "pp", None)
    if value is None and isinstance(entry, Mapping):
        value = entry.get("pp")
    if value is None:
        value = get_raw(entry).get("pp")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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

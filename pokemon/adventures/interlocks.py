"""Persisted-state Adventure gates independent of volatile battle caches.

The room's battle ledger and character lock are deliberately treated as
authoritative until normal battle cleanup removes them.  A missing ndb pointer
or a lost handler registry is not evidence that the battle has ended.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

_BATTLE_KEY = re.compile(r"^battle_([0-9]+)_(data|state|logic|encounter|battle_result)$")


def _db_value(obj: Any, key: str, default: Any = None) -> Any:
    """Read an Evennia attribute or the equivalent lightweight test value."""
    db = getattr(obj, "db", None)
    if db is None:
        return default
    try:
        value = getattr(db, key)
    except Exception:
        return default
    return default if value is None else value


def _battle_id(raw: Any) -> int | None:
    """Normalize a stored battle identity without treating absence as zero."""
    if raw is None or raw is False or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _room_index_ids(room: Any) -> set[int]:
    """Read battle identities from the room's persistent index."""
    raw = _db_value(room, "battles", []) or []
    if isinstance(raw, (str, int)):
        raw = [raw]
    try:
        return {bid for item in raw if (bid := _battle_id(item)) is not None}
    except TypeError:
        return set()


def _room_storage_ids(room: Any) -> set[int]:
    """Find durable battle parts even when the room's battle list was lost."""

    names: set[str] = set()
    attrs = getattr(room, "attributes", None)
    if attrs is not None:
        try:
            names.update(str(attribute.key) for attribute in attrs.all())
        except Exception:
            pass
    db = getattr(room, "db", None)
    names.update(str(key) for key in (getattr(db, "__dict__", None) or {}))
    ids = set()
    for key in names:
        match = _BATTLE_KEY.fullmatch(key)
        if match:
            ids.add(int(match.group(1)))
    return ids


def room_battle_ids(room: Any) -> set[int]:
    """Inspect both the room index and persistent battle storage."""

    if room is None:
        return set()
    return _room_index_ids(room) | _room_storage_ids(room)


def _runtime_battle(player: Any) -> Any | None:
    """Find an unfinished battle without relying on one volatile cache."""
    ndb = getattr(player, "ndb", None)
    cached = getattr(ndb, "battle_instance", None)
    if cached is not None and not getattr(cached, "_ended", False):
        return cached
    try:
        from pokemon.battle.handler import battle_handler

        found = battle_handler.for_player(player)
        if found is not None and not getattr(found, "_ended", False):
            return found
    except Exception:
        # Failure to inspect the cache must never discard the durable checks.
        pass
    return None


@dataclass(frozen=True)
class AdventureBattleInterlock:
    """Single action/cleanup decision for a character and optional run."""

    active_battle: bool
    pending_result: bool
    awaiting_encounter: bool
    battle_ids: frozenset[int]

    @property
    def blocked(self) -> bool:
        return self.active_battle or self.pending_result or self.awaiting_encounter

    @property
    def blocks_route_retry(self) -> bool:
        # A route reserved before a failed launch is retryable, but a running
        # or terminal battle must never be replaced with a new encounter.
        return self.active_battle or self.pending_result

    @property
    def message(self) -> str:
        if self.active_battle:
            return "Finish your current battle before continuing your adventure. Use +adventure/retry if its cleanup was interrupted."
        if self.pending_result:
            return "Your encounter result is pending. Use +adventure/retry."
        return "Finish the chosen encounter first. Use +adventure/choose with the same route to retry it."


def inspect_adventure_battle(player: Any, session: Any | None = None) -> AdventureBattleInterlock:
    """Check real battle identity, saved terminal receipts and route state.

    An Adventure room is reserved to one session; its persisted battle index
    also protects against losing *both* the player's db battle ID and ndb
    instance. The route's pending marker protects the gap before launch.
    """

    if player is None and session is not None:
        player = getattr(session, "leader", None)
    room = getattr(session, "instance_room", None) if session is not None else None
    player_ids = {
        bid
        for name in ("battle_id", "battle_lock")
        if (bid := _battle_id(_db_value(player, name))) is not None
    }
    room_ids = room_battle_ids(room)
    runtime = _runtime_battle(player) if player is not None else None
    runtime_id = _battle_id(getattr(runtime, "battle_id", None))
    ids = player_ids | room_ids
    if runtime_id is not None:
        ids.add(runtime_id)

    # A saved result may be the only remaining evidence after battle cleanup.
    receipts = _db_value(player, "pending_adventure_results", {}) or {}
    session_id = getattr(session, "pk", getattr(session, "id", None))
    if isinstance(receipts, Mapping):
        pending_result = (str(session_id) in receipts) if session is not None else bool(receipts)
    else:
        # Corrupt receipts must be repaired, not silently bypassed.
        pending_result = bool(receipts)

    for bid in room_ids:
        result = _db_value(room, f"battle_{bid}_battle_result", {}) or {}
        encounter = _db_value(room, f"battle_{bid}_encounter", {}) or {}
        if (isinstance(encounter, Mapping) and encounter.get("source_type") == "adventure"
                and str(encounter.get("adventure_session_id")) == str(session_id)
                and isinstance(result, Mapping) and result.get("handled") is False):
            pending_result = True

    metadata = getattr(session, "metadata", None) or {}
    awaiting = isinstance(metadata, Mapping) and metadata.get("encounter_state") == "pending"

    # A character's persisted battle lock is sufficient on its own. Room
    # battle evidence belongs to the session even when character refs vanish.
    active = bool(player_ids or room_ids or runtime)
    return AdventureBattleInterlock(
        active_battle=active,
        pending_result=pending_result,
        awaiting_encounter=awaiting,
        battle_ids=frozenset(ids),
    )

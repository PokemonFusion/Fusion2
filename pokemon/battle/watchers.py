"""Helpers for managing battle watchers and observers."""

from __future__ import annotations

from typing import Any, List, Optional

from .compat import log_info, search_object
from .state import BattleState


# ---------------------------------------------------------------------------
# Core watcher helpers
# ---------------------------------------------------------------------------

def add_watcher(state: BattleState, watcher) -> None:
    """Register ``watcher`` for notifications on this battle.

    Parameters
    ----------
    state:
        The :class:`~pokemon.battle.state.BattleState` storing watcher ids.
    watcher:
        Object with an ``id`` attribute identifying the watcher.
    """

    if state.watchers is None:
        state.watchers = set()
    state.watchers.add(getattr(watcher, "id", 0))


def remove_watcher(state: BattleState, watcher) -> None:
    """Remove ``watcher`` from the battle."""

    if state.watchers:
        state.watchers.discard(getattr(watcher, "id", 0))


def notify_watchers(state: BattleState, message: str, room=None) -> None:
    """Send ``message`` to all registered watchers.

    Parameters
    ----------
    state:
        The battle state maintaining watcher ids.
    message:
        Text to send to each watcher.
    room:
        Optional room; if given only watchers currently in this room are
        notified.  This mirrors the behaviour of the original game where
        spectators must remain in the battle room to receive updates.
    """

    if not state.watchers:
        return
    for wid in list(state.watchers):
        objs = search_object(f"#{wid}")
        if not objs:
            continue
        watcher = objs[0]
        if room and watcher.location != room:
            continue
        if watcher.attributes.get("battle_ignore_notify"):
            continue
        watcher.msg(message)


def normalize_watchers(val: Any) -> List[int]:
    """Return a list of watcher ids from ``val``."""

    if isinstance(val, list):
        return [int(x) for x in val if isinstance(x, (int, str))]
    if isinstance(val, set):
        return [int(x) for x in val]
    if isinstance(val, str):
        s = val.strip()
        if s.startswith("{") and s.endswith("}"):
            s = s[1:-1]
        out: List[int] = []
        for part in s.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                out.append(int(part))
            except Exception:
                continue
        return out
    return []


# ---------------------------------------------------------------------------
# Mixin providing watcher management for battle classes
# ---------------------------------------------------------------------------

class WatcherManager:
    """Mixin adding watcher and observer management to battle classes."""

    watchers: set[int]
    observers: set
    state: Optional[BattleState]
    room: Optional[object]

    def add_watcher(self, watcher) -> None:
        if not getattr(self, "state", None):
            return
        add_watcher(self.state, watcher)
        wid = getattr(watcher, "id", None)
        if wid is not None:
            self.watchers.add(wid)
            if hasattr(self, "ndb") and hasattr(self.ndb, "watchers_live"):
                self.ndb.watchers_live.add(wid)
        watcher.ndb.battle_instance = self
        if hasattr(watcher, "db"):
            watcher.db.battle_id = getattr(self, "battle_id", None)
        log_info(f"Watcher {getattr(watcher, 'key', watcher)} added")

    def remove_watcher(self, watcher) -> None:
        if not getattr(self, "state", None):
            return
        remove_watcher(self.state, watcher)
        wid = getattr(watcher, "id", None)
        if wid is not None:
            self.watchers.discard(wid)
            if hasattr(self, "ndb") and hasattr(self.ndb, "watchers_live"):
                self.ndb.watchers_live.discard(wid)
        log_info(f"Watcher {getattr(watcher, 'key', watcher)} removed")

    def notify(self, message: str) -> None:
        if not getattr(self, "state", None):
            return
        notify_watchers(self.state, message, room=getattr(self, "room", None))
        log_info(f"Notified watchers: {message}")

    # ------------------------------------------------------------
    # Observer helpers
    # ------------------------------------------------------------

    def add_observer(self, watcher) -> None:
        """Register ``watcher`` as an observer of this battle."""

        if watcher not in getattr(self, "observers", set()):
            self.observers.add(watcher)
            self.add_watcher(watcher)
            self.msg(f"{watcher.key} is now watching the battle.")
            log_info(f"Observer {getattr(watcher, 'key', watcher)} added")

    def remove_observer(self, watcher) -> None:
        if watcher in getattr(self, "observers", set()):
            self.observers.discard(watcher)
            self.remove_watcher(watcher)
            if getattr(watcher.ndb, "battle_instance", None) == self:
                del watcher.ndb.battle_instance
            log_info(f"Observer {getattr(watcher, 'key', watcher)} removed")


__all__ = [
    "add_watcher",
    "remove_watcher",
    "notify_watchers",
    "normalize_watchers",
    "WatcherManager",
]

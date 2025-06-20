"""Battle interface helper functions converted from legacy MUF code."""

from __future__ import annotations

from evennia import search_object

from .state import BattleState


# ---------------------------------------------------------------------------
# Watcher management
# ---------------------------------------------------------------------------

def add_watcher(state: BattleState, watcher) -> None:
    """Register a watcher for battle notifications."""
    if not state.watchers:
        state.watchers = {}
    state.watchers[watcher.id] = 1


def remove_watcher(state: BattleState, watcher) -> None:
    """Remove a watcher from the battle."""
    if state.watchers and watcher.id in state.watchers:
        del state.watchers[watcher.id]


def notify_watchers(state: BattleState, message: str, room=None) -> None:
    """Send `message` to all watchers currently present."""
    if not state.watchers:
        return
    for wid in list(state.watchers.keys()):
        objs = search_object(wid)
        if not objs:
            continue
        watcher = objs[0]
        if room and watcher.location != room:
            continue
        if watcher.attributes.get("battle_ignore_notify"):
            continue
        watcher.msg(message)

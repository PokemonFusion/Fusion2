"""Battle interface helper functions converted from legacy MUF code."""

from __future__ import annotations

from evennia import search_object
from utils.battle_display import render_battle_ui

from .state import BattleState


# ---------------------------------------------------------------------------
# Watcher management
# ---------------------------------------------------------------------------

def add_watcher(state: BattleState, watcher) -> None:
    """Register a watcher for battle notifications."""
    if state.watchers is None:
        state.watchers = set()
    state.watchers.add(getattr(watcher, "id", 0))


def remove_watcher(state: BattleState, watcher) -> None:
    """Remove a watcher from the battle."""
    if state.watchers:
        state.watchers.discard(getattr(watcher, "id", 0))


def notify_watchers(state: BattleState, message: str, room=None) -> None:
    """Send `message` to all watchers currently present."""
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


def format_turn_banner(turn: int) -> str:
    """Return a simple banner for turn notifications."""
    return f"╭─ Turn {turn} ─╮"


def display_battle_interface(
    trainer,
    opponent,
    battle_state,
    *,
    viewer_team=None,
    waiting_on=None,
) -> str:
    """Return a formatted battle interface string using the new renderer.

    Parameters
    ----------
    trainer, opponent:
        The two trainers participating in battle.
    battle_state:
        Object providing weather, field and round information.
    viewer_team:
        "A", "B" or ``None`` to indicate which side the viewer belongs to.
    waiting_on:
        Optional Pokémon instance to indicate which combatant has not yet
        selected an action.  When provided a footer line is displayed showing
        which Pokémon the system is waiting on.
    """

    class _StateAdapter:
        """Light adapter exposing the API expected by the renderer."""

        def __init__(self, trainer, opponent, state):
            self._trainers = {"A": trainer, "B": opponent}
            self._state = state

        def get_side(self, viewer):
            if viewer is self._trainers["A"]:
                return "A"
            if viewer is self._trainers["B"]:
                return "B"
            return None

        def get_trainer(self, side):
            return self._trainers.get(side)

        @property
        def weather(self):
            return getattr(self._state, "weather", getattr(self._state, "roomweather", "-"))

        @property
        def field(self):
            return getattr(self._state, "field", "-")

        @property
        def round_no(self):
            return getattr(self._state, "round", getattr(self._state, "turn", 0))

    viewer = trainer if viewer_team == "A" else opponent if viewer_team == "B" else None
    adapter = _StateAdapter(trainer, opponent, battle_state)
    return render_battle_ui(adapter, viewer, total_width=78, waiting_on=waiting_on)

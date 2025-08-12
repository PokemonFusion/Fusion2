"""Battle interface helper functions converted from legacy MUF code."""

from __future__ import annotations

from utils.battle_display import render_battle_ui

from .watchers import add_watcher, notify_watchers, remove_watcher


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

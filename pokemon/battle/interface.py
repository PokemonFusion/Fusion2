"""Battle interface helper functions converted from legacy MUF code."""

from __future__ import annotations

from utils.battle_display import render_battle_ui

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

        # Optional battle flavor if the engine exposes it
        encounter_kind = property(lambda self: getattr(self._state, "encounter_kind", ""))

    viewer = trainer if viewer_team == "A" else opponent if viewer_team == "B" else None
    adapter = _StateAdapter(trainer, opponent, battle_state)
    return render_battle_ui(adapter, viewer, total_width=78, waiting_on=waiting_on)


from .watchers import add_watcher, notify_watchers, remove_watcher


def render_interfaces(captain_a, captain_b, state, *, waiting_on=None):
    """Return interface strings for both sides and observers.

    This helper centralises construction of the per-side battle UI.  It wraps
    :func:`display_battle_interface` for the two trainers and for watchers so
    the caller can simply broadcast the returned strings to the appropriate
    audiences.

    Parameters
    ----------
    captain_a, captain_b:
        The trainers heading the A and B sides of the battle.
    state:
        The current battle state object.
    waiting_on:
        Optional Pokémon instance indicating which combatant has yet to choose
        an action.  When provided a footer showing the waiting Pokémon will be
        displayed.

    Returns
    -------
    tuple[str, str, str]
        Interface text for team A members, team B members and observers
        respectively.
    """

    iface_a = display_battle_interface(
        captain_a, captain_b, state, viewer_team="A", waiting_on=waiting_on
    )
    iface_b = display_battle_interface(
        captain_b, captain_a, state, viewer_team="B", waiting_on=waiting_on
    )
    iface_w = display_battle_interface(
        captain_a, captain_b, state, viewer_team=None, waiting_on=waiting_on
    )
    return iface_a, iface_b, iface_w


def broadcast_interfaces(session, *, waiting_on=None) -> None:
    """Render and send interfaces for ``session`` to all participants."""

    iface_a, iface_b, iface_w = render_interfaces(
        session.captainA, session.captainB, session.state, waiting_on=waiting_on
    )
    for t in getattr(session, "teamA", []):
        session._msg_to(t, iface_a)
    for t in getattr(session, "teamB", []):
        session._msg_to(t, iface_b)
    for w in getattr(session, "observers", []):
        session._msg_to(w, iface_w)

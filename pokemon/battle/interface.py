"""Battle interface helper functions converted from legacy MUF code."""

from __future__ import annotations

import logging

from utils.battle_display import render_battle_ui

logger = logging.getLogger(__name__)


def format_turn_banner(turn: int, *, closing: bool = False) -> str:
        """Return a simple banner for turn notifications.

        Parameters
        ----------
        turn:
                The turn number to display.
        closing:
                When ``True`` render the closing variant of the banner so the
                artwork points upward, indicating the end of the turn.
        """

        left = "╰" if closing else "╭"
        right = "╯" if closing else "╮"
        return f"{left}─ Turn {turn} ─{right}"


# -----------------------------------------------------------------------------
# Optional compact prefix for non-UI battle notes
# -----------------------------------------------------------------------------
# Set this to True to globally prefix non-UI one-liners. You can also override
# per call by passing use_prefix=... to send_battle_note/broadcast_note.
PREF_BATTLE_PREFIX: bool = False


def _battle_tag(session) -> str:
	"""
	Build a short, ANSI-safe tag like: 'Btl 123: Spike–Yang' or
	'Btl 123: Spike–Wild Geodude' for wild encounters.
	"""
	# Try common identifiers, fall back to id(session)
	sid = getattr(session, "id", None) or getattr(session, "uuid", None) or id(session)
	sid = str(sid)
	# Keep last 3-4 chars for brevity
	short = sid[-3:]
	a = getattr(session, "captainA", None)
	b = getattr(session, "captainB", None)
	state = getattr(session, "state", None)
	name_a = getattr(a, "name", getattr(a, "key", "?"))
	kind = (getattr(state, "encounter_kind", "") or "").lower()
	if kind == "wild":
		mon = getattr(getattr(b, "active_pokemon", None), "name", "Wild Pokémon")
		title = f"{name_a}–Wild {mon}"
	else:
		name_b = getattr(b, "name", getattr(b, "key", "?"))
		title = f"{name_a}–{name_b}"
	return f"Btl {short}: {title}"


def send_battle_note(session, to, text: str, *, use_prefix: bool | None = None) -> None:
	"""
	Send a one-line message related to the battle. Optionally prefix with a compact tag.
	Use for log-style lines like 'The battle awaits your move.' or damage summaries.
	"""
	if use_prefix is None:
		use_prefix = PREF_BATTLE_PREFIX
	prefix = f"|W[{_battle_tag(session)}]|n " if use_prefix else ""
	session._msg_to(to, f"{prefix}{text}")


def broadcast_note(session, text: str, *, use_prefix: bool | None = None) -> None:
	"""Broadcast a one-line note to both teams and observers, with optional prefix."""
	for t in getattr(session, "teamA", []):
		send_battle_note(session, t, text, use_prefix=use_prefix)
	for t in getattr(session, "teamB", []):
		send_battle_note(session, t, text, use_prefix=use_prefix)
	for w in getattr(session, "observers", []):
		send_battle_note(session, w, text, use_prefix=use_prefix)


def display_battle_interface(
	captain_a,
	captain_b,
	battle_state,
	*,
	viewer_team: str | None = None,
	waiting_on=None,
	) -> str:
	"""Return a formatted battle interface string using the new renderer.
	
	``captain_a`` and ``captain_b`` must always be supplied in this A/B
	order.  The ``viewer_team`` argument then determines which side's
	player sees absolute HP values; the opposite side will see
	percentages.  Invalid values default to observer mode and emit a
	warning.
	
	Parameters
	----------
	captain_a, captain_b:
	        The trainers heading the A and B sides of the battle.
	battle_state:
	        Object providing weather, field and round information.
	viewer_team:
	        "A", "B" or ``None`` to indicate which side the viewer belongs to
	        and therefore which side receives absolute HP values. Any other
	        value is treated as ``None``.
	waiting_on:
	        Optional Pokémon instance to indicate which combatant has not yet
	        selected an action.  When provided a footer line is displayed showing
	        which Pokémon the system is waiting on.
	"""

	if viewer_team not in ("A", "B", None):
		logger.warning(
			"Invalid viewer_team %r; defaulting to observer view", viewer_team
		)
		viewer_team = None

	class _StateAdapter:
		"""Light adapter exposing the API expected by the renderer."""

		def __init__(self, captain_a, captain_b, state):
			self._captains = {"A": captain_a, "B": captain_b}
			self._state = state

		def get_side(self, viewer):
			if viewer is self._captains["A"]:
				return "A"
			if viewer is self._captains["B"]:
				return "B"
			return None

		def get_trainer(self, side):
			return self._captains.get(side)

		@property
		def weather(self):
			return getattr(self._state, "weather", getattr(self._state, "roomweather", "-"))

		@property
		def field(self):
			return getattr(self._state, "field", "-")

		@property
		def round_no(self):
			return getattr(self._state, "round", getattr(self._state, "turn", 0))

		# Optional, used by UI title and _battle_tag for wild encounters
		encounter_kind = property(lambda self: getattr(self._state, "encounter_kind", ""))

	viewer = (
		captain_a if viewer_team == "A" else captain_b if viewer_team == "B" else None
	)
	adapter = _StateAdapter(captain_a, captain_b, battle_state)
	return render_battle_ui(adapter, viewer, total_width=78, waiting_on=waiting_on)


def render_interfaces(captain_a, captain_b, state, *, waiting_on=None):
	"""Return interface strings for both sides and observers.

	This helper centralises construction of the per-side battle UI.  It wraps
:func:`display_battle_interface` for the two captains and for watchers so
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

# ``display_battle_interface`` always expects the captains in A/B order and
# relies on ``viewer_team`` to determine perspective.  Pass ``captain_a`` and
# ``captain_b`` in that order for every call so the helper remains consistent
# for all viewers.
	iface_a = display_battle_interface(
	captain_a,
	captain_b,
	state,
	viewer_team="A",
	waiting_on=waiting_on,
	)
	iface_b = display_battle_interface(
	captain_a,
	captain_b,
	state,
	viewer_team="B",
	waiting_on=waiting_on,
	)
	iface_w = display_battle_interface(
	captain_a,
	captain_b,
	state,
	viewer_team=None,
	waiting_on=waiting_on,
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


def send_interface_to(session, target, *, waiting_on=None) -> None:
        """Render and send the battle interface for ``target`` only."""

        if not target:
                return

        iface_a, iface_b, iface_w = render_interfaces(
                session.captainA, session.captainB, session.state, waiting_on=waiting_on
        )
        if target in getattr(session, "teamA", []):
                session._msg_to(target, iface_a)
        elif target in getattr(session, "teamB", []):
                session._msg_to(target, iface_b)
        elif target in getattr(session, "observers", []):
                session._msg_to(target, iface_w)
        else:
                # Default to the observer view for any untracked recipient so the
                # interface still renders from a neutral perspective.
                session._msg_to(target, iface_w)

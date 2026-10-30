"""Battle interface helper functions converted from legacy MUF code."""

from __future__ import annotations

import logging

from pokemon.ui.battle_render import DEFAULT_BATTLE_UI_STYLE, normalize_battle_ui_style, _iter_viewer_sessions
from utils.battle_display import render_battle_ui
from pokemon.ui.compact_battle import BattleText, same_character, screen_reader

logger = logging.getLogger(__name__)
_DEFAULT_VIEWER = object()


def get_battle_ui_style(target) -> str:
	"""Return the target's selected battle UI style."""

	db = getattr(target, "db", None)
	return normalize_battle_ui_style(getattr(db, "battle_ui_style", None))


def get_battle_ui_width(target, default: int = 78) -> int:
	"""Return a conservative battle UI width for ``target``."""

	ndb = getattr(target, "ndb", None)
	candidates = [
		getattr(ndb, "cols", None),
		getattr(getattr(target, "db", None), "cols", None),
	]
	for client_session in _iter_viewer_sessions(target):
		width = (getattr(client_session, "protocol_flags", None) or {}).get("SCREENWIDTH")
		if isinstance(width, dict):
			width = width.get(0, width.get("0"))
		candidates.append(width)
	for candidate in candidates:
		try:
			if candidate:
				return max(24, min(int(candidate) - 2, 80))
		except (TypeError, ValueError):
			continue
	return default


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

        edge = "-" if closing else "="
        return f"{edge * 2} Turn {turn} {edge * 2}"


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
	style: str | None = None,
	total_width: int | None = None,
	viewer=_DEFAULT_VIEWER,
	session=None,
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
	style:
		Optional renderer style: ``compact``, ``legacy``, ``classic_modern`` or ``pf1``.
		When omitted, the viewer's ``db.battle_ui_style`` preference is used
		and falls back to ``compact``.
	total_width:
		Optional target width.  When omitted, ``target.ndb.cols`` is used if
		available, capped for ordinary MUD clients.
	viewer:
		Actual recipient, when available. Ownership and preferences are resolved
		for this character rather than borrowing the selected captain's identity.
	session:
		Optional live session supplying every physical cell and its controller.
	"""

	if viewer_team not in ("A", "B", None):
		logger.warning(
			"Invalid viewer_team %r; defaulting to observer view", viewer_team
		)
		viewer_team = None
	if session is None:
		session = getattr(getattr(captain_a, "ndb", None), "battle_instance", None)
	if viewer is _DEFAULT_VIEWER:
		viewer = captain_a if viewer_team == "A" else captain_b if viewer_team == "B" else None
	else:
		members_a = getattr(session, "teamA", None) or [captain_a]
		members_b = getattr(session, "teamB", None) or [captain_b]
		viewer_team = ("A" if any(same_character(viewer, member) for member in members_a)
				   else "B" if any(same_character(viewer, member) for member in members_b) else None)

	class _StateAdapter:
		"""Light adapter exposing the API expected by the renderer."""

		def __init__(self, captain_a, captain_b, state):
			self._captains = {"A": captain_a, "B": captain_b}
			self._state = state
			self.session = session

		def get_side(self, viewer):
			return viewer_team

		def get_trainer(self, side):
			return self._captains.get(side)

		@property
		def weather(self):
			field = getattr(getattr(self.session, "battle", None), "field", None)
			if field is not None and hasattr(field, "weather"):
				return field.weather or "clear"
			return getattr(self._state, "weather", getattr(self._state, "roomweather", "-"))

		@property
		def field(self):
			field = getattr(getattr(self.session, "battle", None), "field", None)
			conditions = []
			terrain = getattr(field, "terrain", None)
			if terrain:
				conditions.append(str(terrain))
			room = getattr(field, "pseudo_weather", {}).get("trickroom")
			if room:
				remaining = room.get("duration") if isinstance(room, dict) else None
				conditions.append(f"Trick Room ({remaining})" if remaining is not None else "Trick Room")
			return " / ".join(conditions) or getattr(self._state, "field", "-")

		@property
		def round_no(self):
			return getattr(self._state, "round", getattr(self._state, "turn", 0))

		# Optional, used by UI title and _battle_tag for wild encounters
		encounter_kind = property(lambda self: getattr(self._state, "encounter_kind", ""))

	if style is None:
		style = get_battle_ui_style(viewer) if viewer is not None else DEFAULT_BATTLE_UI_STYLE
	else:
		style = normalize_battle_ui_style(style)
	if total_width is None:
		total_width = get_battle_ui_width(viewer) if viewer is not None else 78
	adapter = _StateAdapter(captain_a, captain_b, battle_state)
	output = render_battle_ui(
		adapter,
		viewer,
		total_width=total_width,
		waiting_on=waiting_on,
		style=style,
	)
	# Older styles still need explicit form labels for their second active slot.
	# Retain an explicitly supplied session, including an observer's redraw.
	positions = getattr(getattr(getattr(session, "data", None), "turndata", None), "positions", {})
	compact = style == "compact" or screen_reader(viewer)
	for label, position in (() if compact else positions.items()):
		mon = getattr(position, "pokemon", None)
		tera = getattr(mon, "terastallized", None)
		if tera:
			output += f"\n{label}: Tera {tera} ({getattr(mon, 'name', 'Pokemon')})"
		if getattr(mon, "mega_evolved", False):
			output += f"\n{label}: Mega {mon.species} ({mon.name})"
	for side, request in getattr(getattr(session, "battle", None), "mega_pending", {}).items():
		if side == viewer_team:
			output += f"\n{side}: Mega reserved for {request.get('target')} (choose +attack)."
	for side in sorted(getattr(getattr(session, "battle", None), "mega_used", set())):
		output += f"\n{side}: Mega Evolution use spent."
	for side, request in getattr(getattr(session, "battle", None), "z_pending", {}).items():
		if side == viewer_team:
			output += f"\n{side}: Z-Move queued from {request.get('source')} toward {request.get('target')}."
	for side in sorted(getattr(getattr(session, "battle", None), "z_used", set())):
		output += f"\n{side}: Z-Move use spent."
	if compact:
		text = BattleText(total_width, screen_reader(viewer))
		text.add(output)
		return text.render()
	return output


def render_interfaces(captain_a, captain_b, state, *, waiting_on=None, style: str | None = None):
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
	style:
		Optional renderer style to use for all returned interfaces.

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
	style=style,
	)
	iface_b = display_battle_interface(
	captain_a,
	captain_b,
	state,
	viewer_team="B",
	waiting_on=waiting_on,
	style=style,
	)
	iface_w = display_battle_interface(
	captain_a,
	captain_b,
	state,
	viewer_team=None,
	waiting_on=waiting_on,
	style=style,
	)
	return iface_a, iface_b, iface_w


def broadcast_interfaces(session, *, waiting_on=None) -> None:
        """Render and send interfaces for ``session`` to all participants."""
        for t in getattr(session, "teamA", []):
                send_interface_to(session, t, waiting_on=waiting_on)
        for t in getattr(session, "teamB", []):
                send_interface_to(session, t, waiting_on=waiting_on)
        for w in getattr(session, "observers", []):
                send_interface_to(session, w, waiting_on=waiting_on)


def send_interface_to(session, target, *, waiting_on=None) -> None:
        """Render and send the battle interface for ``target`` only."""

        if not target:
                return
        if (getattr(getattr(session, 'state', None), 'multi', None)
                and get_battle_ui_style(target) != "compact" and not screen_reader(target)):
                from .multi_battle import field_text
                session._msg_to(target, field_text(session))
                return

        if target in getattr(session, "teamA", []):
                viewer_team = "A"
        elif target in getattr(session, "teamB", []):
                viewer_team = "B"
        else:
                # Default to the observer view for any untracked recipient so the
                # interface still renders from a neutral perspective.
                viewer_team = None
        session._msg_to(
                target,
                display_battle_interface(
                        session.captainA,
                        session.captainB,
                        session.state,
                        viewer_team=viewer_team,
                        waiting_on=waiting_on,
                        style=get_battle_ui_style(target),
                        total_width=get_battle_ui_width(target),
                        viewer=target,
                        session=session,
                ),
        )


def publish_compact_events(session) -> None:
    """Deliver the final turn's committed events when no further HUD will follow."""
    from pokemon.ui.compact_battle import BattleEventPresentation, uses_compact

    events = getattr(session, "_battle_ui_last_events", [])
    if not events:
        return
    targets = [*getattr(session, "teamA", []), *getattr(session, "teamB", []),
               *getattr(session, "observers", [])]
    for target in targets:
        if uses_compact(target):
            text = BattleText(get_battle_ui_width(target), screen_reader(target))
            text.add("|WLAST TURN|n")
            for message in events:
                text.add(BattleEventPresentation.format(message))
            session._msg_to(target, text.render())

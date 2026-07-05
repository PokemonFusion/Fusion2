"""Staff recovery/debug command for Adventure Mode Alpha."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

try:
    from evennia import Command as _EvenniaCommand
except Exception:  # pragma: no cover - lightweight test fallback
    _EvenniaCommand = None
if _EvenniaCommand is None:  # pragma: no cover - lightweight test fallback
    class Command:  # type: ignore[no-redef]
        pass
else:
    Command = _EvenniaCommand

try:
    from world.stale_state import cleanup_stale_state, format_cleanup_counts
except Exception:  # pragma: no cover - cleanup may be unavailable in lightweight tests
    cleanup_stale_state = None
    format_cleanup_counts = None

from pokemon.adventures import sessions
from pokemon.adventures.cmdsets import detach_movement_cmdset
from pokemon.adventures.commands import _parse_slash_switches
from pokemon.adventures.constants import (
    ADVENTURE_HALL_ATTR,
    ADVENTURE_SESSION_ATTR,
    STATE_ABANDONED,
    STATE_ACTIVE,
    STATE_COMPLETED,
)
from pokemon.adventures.renderer import render_session, render_template_info
from pokemon.adventures.templates import (
    get_template,
    initial_objective_progress,
    list_templates,
    validate_template,
)


class CmdAdventureAdmin(Command):
    """Inspect and recover Adventure sessions.

    Usage:
      +adventureadmin/list
      +adventureadmin/info <session_id>
      +adventureadmin/abort <session_id>
      +adventureadmin/return <player>
      +adventureadmin/cleanup
      +adventureadmin/validate <template|all>
      +adventureadmin/preview <template> [node]
    """

    key = "+adventureadmin"
    aliases = ["+advadmin"]
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def parse(self):
        _parse_slash_switches(self)

    def func(self):
        action, arg = self._action_and_arg()
        if action == "list":
            self._list()
        elif action == "info":
            self._info(arg)
        elif action == "abort":
            self._abort(arg)
        elif action == "return":
            self._return_player(arg)
        elif action == "cleanup":
            self._cleanup()
        elif action == "validate":
            self._validate(arg)
        elif action == "preview":
            self._preview(arg)
        else:
            self.caller.msg(_usage())

    def _action_and_arg(self) -> tuple[str, str]:
        switches = getattr(self, "switches", set())
        for action in ("list", "info", "abort", "return", "cleanup", "validate", "preview"):
            if action in switches:
                return action, (self.args or "").strip()
        raw = (self.args or "").strip()
        if not raw:
            return "help", ""
        first, _, rest = raw.partition(" ")
        first = first.lower()
        if first in {"list", "info", "abort", "return", "cleanup", "validate", "preview"}:
            return first, rest.strip()
        return "help", raw

    def _list(self) -> None:
        current = _current_sessions()
        if not current:
            self.caller.msg("No current Adventure sessions.")
            return
        lines = ["Current Adventure sessions:"]
        for session in current:
            lines.append(
                "  "
                f"#{_session_id(session)} "
                f"player={_object_name(getattr(session, 'leader', None))} "
                f"template={getattr(session, 'template_key', '')} "
                f"state={getattr(session, 'state', '')} "
                f"room={_object_name(getattr(session, 'instance_room', None))} "
                f"node={getattr(session, 'current_node', '')} "
                f"age={_age_text(session)} "
                f"expiry={_expiry_text(session)}"
            )
        self.caller.msg("\n".join(lines))

    def _info(self, arg: str) -> None:
        session = _get_session_or_report(self.caller, arg, "info")
        if session is None:
            return
        self.caller.msg(_render_session_info(session))

    def _abort(self, arg: str) -> None:
        session = _get_session_or_report(self.caller, arg, "abort")
        if session is None:
            return
        if not _is_admin_current_session(session):
            self.caller.msg("That Adventure session is not active or completed-not-left.")
            return
        completed = getattr(session, "state", None) == STATE_COMPLETED
        _end_session(session)
        outcome = "completed session cleaned up" if completed else "session abandoned"
        self.caller.msg(f"Adventure session #{_session_id(session)} aborted: {outcome}.")

    def _return_player(self, arg: str) -> None:
        if not arg:
            self.caller.msg("Usage: +adventureadmin/return <player>")
            return
        target = _search_player(self.caller, arg)
        if target is None:
            self.caller.msg("No such player.")
            return
        session = sessions.get_current_session_for_player(target)
        if session is None:
            self.caller.msg(f"{_object_name(target)} has no current Adventure session.")
            return
        _end_session(session)
        self.caller.msg(f"Returned {_object_name(target)} from Adventure session #{_session_id(session)}.")

    def _cleanup(self) -> None:
        if cleanup_stale_state is None or format_cleanup_counts is None:
            self.caller.msg("Adventure cleanup is unavailable.")
            return
        counts = cleanup_stale_state()
        self.caller.msg("Adventure cleanup ran: " + format_cleanup_counts(counts))

    def _validate(self, arg: str) -> None:
        if not arg:
            self.caller.msg("Usage: +adventureadmin/validate <template|all>")
            return
        templates = list_templates() if arg.strip().lower() == "all" else [get_template(arg)]
        if not templates or any(template is None for template in templates):
            self.caller.msg("No adventure by that name was found.")
            return
        lines = ["Adventure template validation:"]
        for template in templates:
            errors = validate_template(template)
            if errors:
                lines.append(f"  {template.key}: ERROR")
                lines.extend(f"    - {error}" for error in errors)
            else:
                lines.append(f"  {template.key}: OK")
        self.caller.msg("\n".join(lines))

    def _preview(self, arg: str) -> None:
        if not arg:
            self.caller.msg("Usage: +adventureadmin/preview <template> [node]")
            return
        template_key, _, node_key = arg.partition(" ")
        template = get_template(template_key if node_key else arg)
        if template is None:
            self.caller.msg("No adventure by that name was found.")
            return
        node_key = node_key.strip()
        if not node_key:
            self.caller.msg(render_template_info(template))
            return
        if node_key not in template.nodes:
            self.caller.msg(f"Node '{node_key}' was not found in {template.key}.")
            return
        visited = [template.start_node]
        if node_key not in visited:
            visited.append(node_key)
        fake_session = SimpleNamespace(
            template_key=template.key,
            current_node=node_key,
            visited_nodes=visited,
            objective_progress=initial_objective_progress(template),
            state=STATE_ACTIVE,
        )
        self.caller.msg(render_session(fake_session))


def _usage() -> str:
    return (
        "Usage: +adventureadmin/list | +adventureadmin/info <session_id> | "
        "+adventureadmin/abort <session_id> | +adventureadmin/return <player> | "
        "+adventureadmin/cleanup | +adventureadmin/validate <template|all> | "
        "+adventureadmin/preview <template> [node]"
    )


def _query_sessions_by_state(state: str) -> list[Any]:
    model = sessions._session_model()
    try:
        return list(model.objects.filter(state=state))
    except TypeError:
        return []


def _current_sessions() -> list[Any]:
    current: list[Any] = []
    for session in _query_sessions_by_state(STATE_ACTIVE):
        if sessions._is_active_session(session):
            current.append(session)
    for session in _query_sessions_by_state(STATE_COMPLETED):
        if _session_has_pointer(session):
            current.append(session)
    return sorted(current, key=lambda session: str(_session_id(session)))


def _is_admin_current_session(session: Any) -> bool:
    if sessions._is_active_session(session):
        return True
    return getattr(session, "state", None) == STATE_COMPLETED and _session_has_pointer(session)


def _session_has_pointer(session: Any) -> bool:
    session_id = _session_id(session)
    leader = getattr(session, "leader", None)
    room = getattr(session, "instance_room", None)
    return sessions._ids_match(sessions._db_attr(leader, ADVENTURE_SESSION_ATTR), session_id) or sessions._ids_match(
        sessions._db_attr(room, ADVENTURE_SESSION_ATTR),
        session_id,
    )


def _session_id(session: Any) -> Any:
    return sessions._session_id(session)


def _get_session_or_report(caller: Any, raw_id: str, action: str) -> Any | None:
    if not raw_id:
        caller.msg(f"Usage: +adventureadmin/{action} <session_id>")
        return None
    session = sessions.get_session_by_id(raw_id)
    if session is None:
        caller.msg("No Adventure session by that ID was found.")
        return None
    return session


def _render_session_info(session: Any) -> str:
    session_id = _session_id(session)
    leader = getattr(session, "leader", None)
    room = getattr(session, "instance_room", None)
    player_pointer = sessions._db_attr(leader, ADVENTURE_SESSION_ATTR)
    room_pointer = sessions._db_attr(room, ADVENTURE_SESSION_ATTR)
    player_matches = sessions._ids_match(player_pointer, session_id)
    room_matches = sessions._ids_match(room_pointer, session_id)
    visited = ", ".join(str(node) for node in (getattr(session, "visited_nodes", None) or [])) or "none"
    progress = getattr(session, "objective_progress", None) or {}
    progress_text = ", ".join(f"{key}={value}" for key, value in sorted(progress.items())) or "none"
    return "\n".join(
        [
            f"Adventure session #{session_id}",
            f"Template: {getattr(session, 'template_key', '')}",
            f"State: {getattr(session, 'state', '')}",
            f"Player: {_object_name(leader)}",
            f"Room: {_object_name(room)}",
            f"Return: {_object_name(getattr(session, 'return_location', None))}",
            f"Current node: {getattr(session, 'current_node', '')}",
            f"Visited nodes: {visited}",
            f"Objective progress: {progress_text}",
            f"Player pointer: {_pointer_text(player_pointer)} (matches: {_yes_no(player_matches)})",
            f"Room pointer: {_pointer_text(room_pointer)} (matches: {_yes_no(room_matches)})",
            f"Pointers match: {_yes_no(player_matches and room_matches)}",
            f"Age: {_age_text(session)}",
            f"Expiry: {_expiry_text(session)}",
        ]
    )


def _end_session(session: Any) -> None:
    completed = getattr(session, "state", None) == STATE_COMPLETED
    if not completed:
        session.state = STATE_ABANDONED
        sessions._save_session(session, fields=("state", "updated_at"))
    _clear_matching_attrs(session)
    leader = getattr(session, "leader", None)
    destination = getattr(session, "return_location", None) or _find_adventure_hall()
    if leader is not None:
        detach_movement_cmdset(leader)
        move_to = getattr(leader, "move_to", None)
        if callable(move_to) and destination is not None and getattr(leader, "location", None) is not destination:
            move_to(destination, quiet=True)


def _clear_matching_attrs(session: Any) -> None:
    session_id = _session_id(session)
    leader = getattr(session, "leader", None)
    room = getattr(session, "instance_room", None)
    if leader is not None:
        sessions._del_db_attr_if_points_to(leader, ADVENTURE_SESSION_ATTR, session_id)
    if room is not None:
        sessions._del_db_attr_if_points_to(room, ADVENTURE_SESSION_ATTR, session_id)


def _find_adventure_hall() -> Any | None:
    for room in sessions._search_object("Adventure Hall"):
        if sessions._db_attr(room, ADVENTURE_HALL_ATTR, False):
            return room
    return None


def _search_player(caller: Any, query: str) -> Any | None:
    search = getattr(caller, "search", None)
    if callable(search):
        try:
            result = search(query, global_search=True)
        except TypeError:
            result = search(query)
        if isinstance(result, (list, tuple)):
            return result[0] if result else None
        return result
    try:
        from evennia import search_object

        results = search_object(query)
        return results[0] if results else None
    except Exception:
        return None


def _object_name(obj: Any) -> str:
    if obj is None:
        return "none"
    key = getattr(obj, "key", None) or str(obj)
    obj_id = getattr(obj, "id", getattr(obj, "pk", None))
    return f"{key} #{obj_id}" if obj_id is not None else key


def _pointer_text(value: Any) -> str:
    return "none" if value in (None, "", False) else str(value)


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _age_text(session: Any) -> str:
    started_at = getattr(session, "started_at", None)
    if started_at is None:
        return "unknown"
    try:
        return _delta_text(sessions._now() - started_at)
    except TypeError:
        return "unknown"


def _expiry_text(session: Any) -> str:
    expires_at = getattr(session, "expires_at", None)
    if expires_at is None:
        return "none"
    try:
        remaining = expires_at - sessions._now()
    except TypeError:
        return "unknown"
    if remaining.total_seconds() <= 0:
        return "expired"
    return "in " + _delta_text(remaining)


def _delta_text(delta: Any) -> str:
    try:
        total_seconds = max(0, int(delta.total_seconds()))
    except Exception:
        return "unknown"
    minutes = total_seconds // 60
    hours = minutes // 60
    if hours:
        return f"{hours}h{minutes % 60:02d}m"
    return f"{minutes}m"

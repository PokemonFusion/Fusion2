"""Adventure session lifecycle and objective helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from typing import Any, Iterable

from django.utils import timezone

from .constants import (
    ADVENTURE_HALL_ATTR,
    ADVENTURE_INSTANCE_ATTR,
    ADVENTURE_SESSION_ATTR,
    DEFAULT_SESSION_MINUTES,
    STATE_ABANDONED,
    STATE_ACTIVE,
    STATE_COMPLETED,
    STATE_EXPIRED,
)
from .templates import (
    AdventureObjective,
    AdventureTemplate,
    get_template,
    initial_objective_progress,
    validate_template,
)


@dataclass
class AdventureActionResult:
    """Return value for player-facing Adventure actions."""

    ok: bool
    message: str
    session: Any | None = None


def _session_model():
    from pokemon.models.adventures import AdventureSession

    return AdventureSession


def _now():
    try:
        return timezone.now()
    except Exception:
        return datetime.now(dt_timezone.utc)


def _db_attr(obj: Any, attr: str, default: Any = None) -> Any:
    db = getattr(obj, "db", None)
    if db is None:
        return default
    try:
        value = getattr(db, attr)
    except Exception:
        return default
    return default if value is None else value


def _set_db_attr(obj: Any, attr: str, value: Any) -> None:
    db = getattr(obj, "db", None)
    if db is not None:
        setattr(db, attr, value)


def _del_db_attr(obj: Any, attr: str) -> None:
    db = getattr(obj, "db", None)
    if db is None:
        return
    try:
        if hasattr(db, attr):
            delattr(db, attr)
    except Exception:
        pass


def _object_id(obj: Any) -> Any:
    if obj is None:
        return None
    return getattr(obj, "id", getattr(obj, "pk", None))


def _ids_match(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return False
    return str(left) == str(right)


def _query_first(queryset: Any) -> Any | None:
    first = getattr(queryset, "first", None)
    if callable(first):
        return first()
    try:
        return next(iter(queryset))
    except StopIteration:
        return None
    except TypeError:
        return None


def _save_session(session: Any, fields: Iterable[str] | None = None) -> None:
    save = getattr(session, "save", None)
    if not callable(save):
        return
    if fields is None:
        save()
        return
    try:
        save(update_fields=list(fields))
    except TypeError:
        save()


def _search_object(query: Any) -> list[Any]:
    if query is None:
        return []
    if not isinstance(query, str):
        return [query]
    try:
        from evennia import search_object
    except Exception:
        return []
    try:
        return list(search_object(query))
    except Exception:
        return []


def get_session_by_id(session_id: Any) -> Any | None:
    """Return an AdventureSession by primary key."""

    if session_id in (None, ""):
        return None
    try:
        resolved_id = int(session_id)
    except (TypeError, ValueError):
        resolved_id = session_id
    model = _session_model()
    try:
        return _query_first(model.objects.filter(pk=resolved_id))
    except Exception:
        return _query_first(model.objects.filter(id=resolved_id))


def _is_expired(session: Any) -> bool:
    expires_at = getattr(session, "expires_at", None)
    if not expires_at:
        return False
    try:
        return expires_at <= _now()
    except TypeError:
        return False


def _is_active_session(session: Any) -> bool:
    if session is None:
        return False
    if getattr(session, "state", None) != STATE_ACTIVE:
        return False
    if getattr(session, "completed_at", None) is not None:
        return False
    if _is_expired(session):
        expire_session(session)
        return False
    return True


def get_active_session_for_player(player: Any) -> Any | None:
    """Return the player's active solo Adventure session, if any."""

    session = get_session_by_id(_db_attr(player, ADVENTURE_SESSION_ATTR))
    if not _is_active_session(session):
        if session is not None:
            _del_db_attr(player, ADVENTURE_SESSION_ATTR)
        return None
    if not _ids_match(getattr(session, "leader_id", _object_id(getattr(session, "leader", None))), _object_id(player)):
        return None
    return session


def get_active_session_for_room(room: Any, looker: Any) -> Any | None:
    """Return the room session visible to ``looker``."""

    room_sid = _db_attr(room, ADVENTURE_SESSION_ATTR)
    player_sid = _db_attr(looker, ADVENTURE_SESSION_ATTR)
    if not room_sid or not _ids_match(room_sid, player_sid):
        return None
    session = get_session_by_id(room_sid)
    if not _is_active_session(session):
        return None
    if not _ids_match(getattr(session, "instance_room_id", _object_id(getattr(session, "instance_room", None))), _object_id(room)):
        return None
    return session


def _as_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.lower() in {"true", "yes", "1", "on"}
    return bool(value)


def _room_exits(room: Any) -> list[Any]:
    contents_get = getattr(room, "contents_get", None)
    if callable(contents_get):
        try:
            return list(contents_get(content_type="exit"))
        except Exception:
            return []
    return [obj for obj in getattr(room, "contents", []) if getattr(obj, "destination", None)]


def _resolve_room_refs(raw_refs: Any) -> list[Any]:
    if not raw_refs:
        return []
    if isinstance(raw_refs, str):
        refs = [part.strip() for part in raw_refs.split(",") if part.strip()]
    elif isinstance(raw_refs, (list, tuple, set)):
        refs = list(raw_refs)
    else:
        refs = [raw_refs]
    rooms: list[Any] = []
    for ref in refs:
        rooms.extend(_search_object(ref))
    return rooms


def find_instance_rooms(hall: Any) -> list[Any]:
    """Find candidate Adventure instance rooms for ``hall``."""

    candidates: list[Any] = []
    candidates.extend(_resolve_room_refs(_db_attr(hall, "adventure_instance_rooms")))
    for exit_obj in _room_exits(hall):
        destination = getattr(exit_obj, "destination", None)
        if destination is not None:
            candidates.append(destination)
    candidates.extend(_search_object("Adventure Instance Room #1"))
    candidates.extend(_search_object("Adventure Instance Room 1"))

    seen: set[str] = set()
    rooms: list[Any] = []
    for room in candidates:
        identifier = str(_object_id(room) or id(room))
        if identifier in seen:
            continue
        seen.add(identifier)
        if _as_bool(_db_attr(room, ADVENTURE_INSTANCE_ATTR, False)):
            rooms.append(room)
    return rooms


def _room_has_active_battle(room: Any) -> bool:
    battles = _db_attr(room, "battles", [])
    return bool(battles)


def room_is_available(room: Any) -> bool:
    """Return whether an Adventure instance room can be reserved."""

    if not _as_bool(_db_attr(room, ADVENTURE_INSTANCE_ATTR, False)):
        return False
    if _room_has_active_battle(room):
        return False
    session_id = _db_attr(room, ADVENTURE_SESSION_ATTR)
    if not session_id:
        return True
    session = get_session_by_id(session_id)
    if _is_active_session(session):
        return False
    _del_db_attr(room, ADVENTURE_SESSION_ATTR)
    return True


def find_available_instance_room(hall: Any) -> Any | None:
    """Return the first unused Adventure instance room for ``hall``."""

    for room in find_instance_rooms(hall):
        if room_is_available(room):
            return room
    return None


def _objective_done(progress: dict[str, int], objective: AdventureObjective) -> bool:
    return int(progress.get(objective.key, 0) or 0) >= 1


def _set_objective_done(progress: dict[str, int], objective: AdventureObjective) -> bool:
    if _objective_done(progress, objective):
        return False
    progress[objective.key] = 1
    return True


def _required_before_return_complete(
    template: AdventureTemplate,
    progress: dict[str, int],
    return_objective: AdventureObjective,
) -> bool:
    for objective in template.objectives:
        if objective is return_objective:
            continue
        if objective.required and not _objective_done(progress, objective):
            return False
    return True


def _all_required_complete(template: AdventureTemplate, progress: dict[str, int]) -> bool:
    return all(not objective.required or _objective_done(progress, objective) for objective in template.objectives)


def _mark_completed(session: Any) -> None:
    if getattr(session, "state", None) == STATE_COMPLETED:
        return
    session.state = STATE_COMPLETED
    session.completed_at = _now()


def update_location_objectives(session: Any) -> bool:
    """Apply objectives caused by the session's current virtual node."""

    template = get_template(getattr(session, "template_key", ""))
    if template is None:
        return False
    progress = dict(getattr(session, "objective_progress", None) or {})
    changed = False
    for objective in template.objectives:
        if objective.target_node != getattr(session, "current_node", ""):
            continue
        if objective.type == "reach":
            changed = _set_objective_done(progress, objective) or changed
        elif objective.type == "return" and _required_before_return_complete(template, progress, objective):
            changed = _set_objective_done(progress, objective) or changed
    if _all_required_complete(template, progress):
        _mark_completed(session)
        changed = True
    session.objective_progress = progress
    return changed


def start_session(player: Any, template_key: str) -> AdventureActionResult:
    """Start a solo Adventure for ``player``."""

    if get_active_session_for_player(player):
        return AdventureActionResult(False, "You are already in an adventure.")

    template = get_template(template_key)
    if template is None:
        return AdventureActionResult(False, "No adventure by that name was found.")
    errors = validate_template(template)
    if errors:
        return AdventureActionResult(False, "Adventure template is not valid: " + "; ".join(errors))

    hall = getattr(player, "location", None)
    if not hall or not _as_bool(_db_attr(hall, ADVENTURE_HALL_ATTR, False)):
        return AdventureActionResult(False, "You need to start adventures from the Adventure Hall.")

    instance_room = find_available_instance_room(hall)
    if instance_room is None:
        return AdventureActionResult(False, "No adventure instance rooms are available right now.")

    model = _session_model()
    now = _now()
    session = model.objects.create(
        template_key=template.key,
        state=STATE_ACTIVE,
        leader=player,
        instance_room=instance_room,
        return_location=hall,
        current_node=template.start_node,
        visited_nodes=[template.start_node],
        objective_progress=initial_objective_progress(template),
        started_at=now,
        expires_at=now + timedelta(minutes=DEFAULT_SESSION_MINUTES),
        metadata={},
    )

    _set_db_attr(player, ADVENTURE_SESSION_ATTR, getattr(session, "pk", getattr(session, "id", None)))
    _set_db_attr(instance_room, ADVENTURE_SESSION_ATTR, getattr(session, "pk", getattr(session, "id", None)))
    move_to = getattr(player, "move_to", None)
    if callable(move_to):
        moved = move_to(instance_room, quiet=True)
        if moved is False:
            leave_session(player, session=session, reason=STATE_ABANDONED, move_player=False)
            return AdventureActionResult(False, "The adventure room could not be entered.")

    return AdventureActionResult(
        True,
        f"Started {template.name}.",
        session=session,
    )


def move_session(player: Any, direction: str) -> AdventureActionResult:
    """Move the player's active Adventure session in a virtual direction."""

    normalized = _normalize_direction(direction)
    session = get_active_session_for_player(player)
    if session is None:
        return AdventureActionResult(False, "You are not in an adventure.")
    template = get_template(getattr(session, "template_key", ""))
    if template is None:
        return AdventureActionResult(False, "This adventure template is missing.", session=session)
    node = template.nodes.get(getattr(session, "current_node", ""))
    if node is None:
        return AdventureActionResult(False, "This adventure location is missing.", session=session)
    target_key = node.exits.get(normalized)
    if not target_key:
        return AdventureActionResult(False, "You can't go that way.", session=session)

    session.current_node = target_key
    visited = list(getattr(session, "visited_nodes", None) or [])
    if target_key not in visited:
        visited.append(target_key)
    session.visited_nodes = visited
    update_location_objectives(session)
    _save_session(
        session,
        fields=("current_node", "visited_nodes", "objective_progress", "state", "completed_at", "updated_at"),
    )
    target_node = template.nodes[target_key]
    message = f"You move {normalized} to {target_node.name}."
    if getattr(session, "state", None) == STATE_COMPLETED:
        message += " Adventure complete. Use +adventure/leave to return."
    return AdventureActionResult(True, message, session=session)


def search_session(player: Any) -> AdventureActionResult:
    """Resolve a search action in the player's current Adventure node."""

    session = get_active_session_for_player(player)
    if session is None:
        return AdventureActionResult(False, "You are not in an adventure.")
    template = get_template(getattr(session, "template_key", ""))
    if template is None:
        return AdventureActionResult(False, "This adventure template is missing.", session=session)
    node = template.nodes.get(getattr(session, "current_node", ""))
    if node is None:
        return AdventureActionResult(False, "This adventure location is missing.", session=session)

    progress = dict(getattr(session, "objective_progress", None) or {})
    objective_key = node.search_objective
    objective = next((obj for obj in template.objectives if obj.key == objective_key), None)
    if objective is not None:
        if _objective_done(progress, objective):
            return AdventureActionResult(True, "You have already completed this search.", session=session)
        progress[objective.key] = 1
        session.objective_progress = progress
        update_location_objectives(session)
        _save_session(session, fields=("objective_progress", "state", "completed_at", "updated_at"))
        return AdventureActionResult(True, node.search_text or "You find what you were looking for.", session=session)

    if node.search_text:
        return AdventureActionResult(True, node.search_text, session=session)
    return AdventureActionResult(True, "You search the area but find no objective clues.", session=session)


def leave_session(
    player: Any,
    *,
    session: Any | None = None,
    reason: str = STATE_ABANDONED,
    move_player: bool = True,
) -> AdventureActionResult:
    """Leave and clean up the player's active Adventure session."""

    session = session or get_session_by_id(_db_attr(player, ADVENTURE_SESSION_ATTR))
    if session is None:
        return AdventureActionResult(False, "You are not in an adventure.")

    template = get_template(getattr(session, "template_key", ""))
    session_name = template.name if template else getattr(session, "template_key", "Adventure")
    instance_room = getattr(session, "instance_room", None)
    return_location = getattr(session, "return_location", None)

    _del_db_attr(player, ADVENTURE_SESSION_ATTR)
    if instance_room is not None and _ids_match(
        _db_attr(instance_room, ADVENTURE_SESSION_ATTR),
        getattr(session, "pk", getattr(session, "id", None)),
    ):
        _del_db_attr(instance_room, ADVENTURE_SESSION_ATTR)

    completed = getattr(session, "state", None) == STATE_COMPLETED
    if not completed:
        session.state = reason
    _save_session(session, fields=("state", "updated_at"))

    if move_player and return_location is not None:
        move_to = getattr(player, "move_to", None)
        if callable(move_to) and getattr(player, "location", None) is not return_location:
            move_to(return_location, quiet=True)

    if completed:
        return AdventureActionResult(True, f"You complete {session_name} and return.", session=session)
    return AdventureActionResult(True, f"You leave {session_name}.", session=session)


def expire_session(session: Any) -> None:
    """Mark a stale Adventure session expired and clear room/player attrs."""

    leader = getattr(session, "leader", None)
    instance_room = getattr(session, "instance_room", None)
    if leader is not None:
        _del_db_attr(leader, ADVENTURE_SESSION_ATTR)
    if instance_room is not None:
        _del_db_attr(instance_room, ADVENTURE_SESSION_ATTR)
    session.state = STATE_EXPIRED
    _save_session(session, fields=("state", "updated_at"))


def sync_player_to_active_session(player: Any) -> Any | None:
    """Return a valid active session for reconnect/reload recovery."""

    session = get_active_session_for_player(player)
    if session is None:
        return None
    instance_room = getattr(session, "instance_room", None)
    if instance_room is not None:
        session_id = getattr(session, "pk", getattr(session, "id", None))
        room_session_id = _db_attr(instance_room, ADVENTURE_SESSION_ATTR)
        if not _ids_match(room_session_id, session_id):
            room_session = get_session_by_id(room_session_id)
            if _is_active_session(room_session):
                return None
            _set_db_attr(instance_room, ADVENTURE_SESSION_ATTR, session_id)

        move_to = getattr(player, "move_to", None)
        player_location = getattr(player, "location", None)
        if callable(move_to) and not _ids_match(_object_id(player_location), _object_id(instance_room)):
            move_to(instance_room, quiet=True)
    return session


def _normalize_direction(direction: str) -> str:
    value = (direction or "").strip().lower()
    aliases = {
        "n": "north",
        "s": "south",
        "e": "east",
        "w": "west",
    }
    return aliases.get(value, value)

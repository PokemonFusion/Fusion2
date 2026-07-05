"""Cleanup helpers for stale runtime locks and session references."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from utils.safe_import import safe_import


BATTLE_STORAGE_PARTS = (
	"data",
	"state",
	"logic",
	"trainers",
	"temp_pokemon_ids",
	"meta",
	"field",
	"active",
	"last_action",
	"debug",
)
ADVENTURE_SESSION_ATTR = "adventure_session_id"
ACTIVE_ADVENTURE_STATE = "active"


def _db(obj: Any) -> Any:
	return getattr(obj, "db", None)


def _get_db(obj: Any, name: str, default: Any = None) -> Any:
	db = _db(obj)
	if db is None:
		return default
	try:
		value = getattr(db, name)
	except Exception:
		return default
	return default if value is None else value


def _set_db(obj: Any, name: str, value: Any) -> None:
	db = _db(obj)
	if db is not None:
		setattr(db, name, value)


def _del_db(obj: Any, name: str) -> bool:
	db = _db(obj)
	if db is None:
		return False
	try:
		if hasattr(db, name):
			delattr(db, name)
			return True
	except Exception:
		return False
	return False


def _object_id(obj: Any) -> int | None:
	value = getattr(obj, "id", getattr(obj, "pk", None))
	try:
		return int(value)
	except (TypeError, ValueError):
		return None


def _int_or_none(value: Any) -> int | None:
	try:
		return int(value)
	except (TypeError, ValueError):
		return None


def _as_list(value: Any) -> list[Any]:
	if value is None:
		return []
	if isinstance(value, list):
		return list(value)
	if isinstance(value, tuple):
		return list(value)
	if isinstance(value, set):
		return list(value)
	try:
		return list(value)
	except TypeError:
		return [value]


def _iter_evennia_objects() -> list[Any]:
	try:
		object_model = safe_import("evennia.objects.models").ObjectDB
		return list(object_model.objects.all())
	except Exception:
		return []


def _active_battle_ids_from_handler() -> set[int]:
	try:
		from pokemon.battle.handler import battle_handler
	except Exception:
		return set()
	return {_id for _id in (_int_or_none(value) for value in getattr(battle_handler, "instances", {}) or {}) if _id is not None}


def resolve_adventure_session(session_id: Any) -> Any | None:
	"""Return an AdventureSession for cleanup checks."""

	try:
		from pokemon.adventures.sessions import get_session_by_id
	except Exception:
		return None
	return get_session_by_id(session_id)


def expire_adventure_session(session: Any) -> None:
	"""Expire an AdventureSession using the adventure service when available."""

	try:
		from pokemon.adventures.sessions import expire_session

		expire_session(session)
	except Exception:
		try:
			session.state = "expired"
			save = getattr(session, "save", None)
			if callable(save):
				save()
		except Exception:
			pass


def _normalize_now(now: datetime | None) -> datetime:
	value = now or datetime.now(timezone.utc)
	if value.tzinfo is None:
		return value.replace(tzinfo=timezone.utc)
	return value.astimezone(timezone.utc)


def _is_expired(session: Any, now: datetime) -> bool:
	expires_at = getattr(session, "expires_at", None)
	if expires_at is None:
		return False
	try:
		if expires_at.tzinfo is None:
			expires_at = expires_at.replace(tzinfo=timezone.utc)
		return expires_at <= now
	except (AttributeError, TypeError):
		return False


def _session_active(session: Any, now: datetime) -> bool:
	if session is None:
		return False
	if getattr(session, "state", None) != ACTIVE_ADVENTURE_STATE:
		return False
	if getattr(session, "completed_at", None) is not None:
		return False
	if _is_expired(session, now):
		expire_adventure_session(session)
		return False
	return True


def _cleanup_battle_refs(obj: Any, active_battle_ids: set[int], counts: dict[str, int]) -> None:
	for attr in ("battle_id", "battle_lock"):
		value = _get_db(obj, attr, None)
		if value in (None, "", False):
			continue
		battle_id = _int_or_none(value)
		if battle_id is None or battle_id not in active_battle_ids:
			if _del_db(obj, attr):
				counts[attr] += 1


def _cleanup_room_battle_storage(room: Any, battle_id: int, counts: dict[str, int]) -> None:
	db = _db(room)
	if db is None:
		return
	for part in BATTLE_STORAGE_PARTS:
		key = f"battle_{battle_id}_{part}"
		try:
			if hasattr(db, key):
				delattr(db, key)
				counts["room_battle_parts"] += 1
		except Exception:
			continue


def _cleanup_room_battle_index(room: Any, active_battle_ids: set[int], counts: dict[str, int]) -> None:
	raw_battles = _get_db(room, "battles", None)
	if not raw_battles:
		return
	entries = _as_list(raw_battles)
	kept: list[Any] = []
	stale_ids: list[int] = []
	for entry in entries:
		battle_id = _int_or_none(entry)
		if battle_id is not None and battle_id in active_battle_ids:
			kept.append(entry)
		else:
			if battle_id is not None:
				stale_ids.append(battle_id)
			counts["room_battle_ids"] += 1
	if len(kept) != len(entries):
		_set_db(room, "battles", kept)
	for battle_id in stale_ids:
		_cleanup_room_battle_storage(room, battle_id, counts)


def _request_host_id(key: Any, request: Any) -> int | None:
	if isinstance(request, dict):
		value = request.get("host_id", key)
	else:
		value = getattr(request, "host_id", key)
	return _int_or_none(value)


def _request_host(request: Any, host_id: int | None, objects_by_id: dict[int, Any]) -> Any | None:
	if host_id is not None and host_id in objects_by_id:
		return objects_by_id[host_id]
	get_host = getattr(request, "get_host", None)
	if callable(get_host):
		try:
			return get_host()
		except Exception:
			return None
	if host_id is None:
		return None
	try:
		evennia = safe_import("evennia")
		matches = evennia.search_object(f"#{host_id}")
		return matches[0] if matches else None
	except Exception:
		return None


def _cleanup_pvp_requests(
	room: Any,
	objects_by_id: dict[int, Any],
	hosted_ids: set[int],
	counts: dict[str, int],
) -> None:
	requests = _get_db(room, "pvp_requests", None)
	if not isinstance(requests, dict) or not requests:
		return
	updated = dict(requests)
	for key, request in list(requests.items()):
		host_id = _request_host_id(key, request)
		host = _request_host(request, host_id, objects_by_id)
		if host is not None and getattr(host, "location", None) is room:
			if host_id is not None:
				hosted_ids.add(host_id)
			continue
		updated.pop(key, None)
		counts["pvp_requests"] += 1
		if host is not None:
			_set_db(host, "pvp_locked", False)
	if len(updated) != len(requests):
		_set_db(room, "pvp_requests", updated)


def _cleanup_pvp_lock(obj: Any, hosted_ids: set[int], counts: dict[str, int]) -> None:
	if not bool(_get_db(obj, "pvp_locked", False)):
		return
	obj_id = _object_id(obj)
	if obj_id is None or obj_id not in hosted_ids:
		_set_db(obj, "pvp_locked", False)
		counts["pvp_locks"] += 1


def _cleanup_adventure_attr(obj: Any, now: datetime, counts: dict[str, int]) -> None:
	session_id = _get_db(obj, ADVENTURE_SESSION_ATTR, None)
	if session_id in (None, "", False):
		return
	session = resolve_adventure_session(session_id)
	if not _session_active(session, now):
		if _del_db(obj, ADVENTURE_SESSION_ATTR):
			counts["adventure_attrs"] += 1


def cleanup_stale_state(
	*,
	objects: Iterable[Any] | None = None,
	active_battle_ids: Iterable[int] | None = None,
	now: datetime | None = None,
) -> dict[str, int]:
	"""Clear stale battle, PVP, adventure, and room battle references."""

	resolved_objects = list(objects) if objects is not None else _iter_evennia_objects()
	active_ids = (
		{_id for _id in (_int_or_none(value) for value in active_battle_ids) if _id is not None}
		if active_battle_ids is not None
		else _active_battle_ids_from_handler()
	)
	current_time = _normalize_now(now)
	counts = {
		"battle_id": 0,
		"battle_lock": 0,
		"room_battle_ids": 0,
		"room_battle_parts": 0,
		"pvp_requests": 0,
		"pvp_locks": 0,
		"adventure_attrs": 0,
	}
	objects_by_id = {
		obj_id: obj
		for obj_id, obj in ((_object_id(obj), obj) for obj in resolved_objects)
		if obj_id is not None
	}
	hosted_pvp_ids: set[int] = set()

	for obj in resolved_objects:
		_cleanup_battle_refs(obj, active_ids, counts)
		_cleanup_room_battle_index(obj, active_ids, counts)
		_cleanup_pvp_requests(obj, objects_by_id, hosted_pvp_ids, counts)
		_cleanup_adventure_attr(obj, current_time, counts)

	for obj in resolved_objects:
		_cleanup_pvp_lock(obj, hosted_pvp_ids, counts)

	return counts


def format_cleanup_counts(counts: dict[str, int]) -> str:
	"""Return a compact human-readable cleanup summary."""

	total = sum(int(value or 0) for value in counts.values())
	if total <= 0:
		return "no stale state found"
	parts = [f"{key}={value}" for key, value in counts.items() if value]
	return "cleared " + ", ".join(parts)


__all__ = ["cleanup_stale_state", "format_cleanup_counts"]

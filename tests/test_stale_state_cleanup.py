from __future__ import annotations

import types
from datetime import datetime, timedelta, timezone

from world import heartbeat, stale_state


def _obj(obj_id: int, **attrs):
	db = types.SimpleNamespace(**attrs)
	return types.SimpleNamespace(id=obj_id, db=db, location=None)


def test_cleanup_clears_stale_battle_refs_and_room_storage():
	char_active = _obj(1, battle_id=10, battle_lock=10)
	char_stale = _obj(2, battle_id=5, battle_lock=5)
	room = _obj(
		100,
		battles=[10, 5, "bad"],
		battle_10_data={"live": True},
		battle_5_data={"stale": True},
		battle_5_state={"stale": True},
	)

	counts = stale_state.cleanup_stale_state(
		objects=[char_active, char_stale, room],
		active_battle_ids={10},
	)

	assert char_active.db.battle_id == 10
	assert char_active.db.battle_lock == 10
	assert not hasattr(char_stale.db, "battle_id")
	assert not hasattr(char_stale.db, "battle_lock")
	assert room.db.battles == [10]
	assert hasattr(room.db, "battle_10_data")
	assert not hasattr(room.db, "battle_5_data")
	assert not hasattr(room.db, "battle_5_state")
	assert counts["battle_id"] == 1
	assert counts["battle_lock"] == 1
	assert counts["room_battle_ids"] == 2
	assert counts["room_battle_parts"] == 2


def test_cleanup_clears_invalid_pvp_requests_and_orphan_locks():
	room = _obj(100, pvp_requests={})
	host = _obj(1, pvp_locked=True)
	host.location = room
	orphan = _obj(2, pvp_locked=True)
	missing_host_request = types.SimpleNamespace(host_id=3)
	valid_request = types.SimpleNamespace(host_id=host.id)
	room.db.pvp_requests = {host.id: valid_request, 3: missing_host_request}

	counts = stale_state.cleanup_stale_state(objects=[room, host, orphan], active_battle_ids=set())

	assert room.db.pvp_requests == {host.id: valid_request}
	assert host.db.pvp_locked is True
	assert orphan.db.pvp_locked is False
	assert counts["pvp_requests"] == 1
	assert counts["pvp_locks"] == 1


def test_cleanup_clears_missing_inactive_and_expired_adventure_attrs(monkeypatch):
	now = datetime(2026, 7, 4, 12, 0, tzinfo=timezone.utc)
	active = types.SimpleNamespace(state="active", completed_at=None, expires_at=now + timedelta(minutes=5))
	inactive = types.SimpleNamespace(state="abandoned", completed_at=None, expires_at=None)
	expired = types.SimpleNamespace(state="active", completed_at=None, expires_at=now - timedelta(minutes=5))
	expired_sessions = []
	sessions = {1: active, 2: inactive, 3: expired}
	objs = [
		_obj(1, adventure_session_id=1),
		_obj(2, adventure_session_id=2),
		_obj(3, adventure_session_id=3),
		_obj(4, adventure_session_id=4),
	]

	monkeypatch.setattr(stale_state, "resolve_adventure_session", lambda session_id: sessions.get(session_id))
	monkeypatch.setattr(stale_state, "expire_adventure_session", lambda session: expired_sessions.append(session))

	counts = stale_state.cleanup_stale_state(objects=objs, active_battle_ids=set(), now=now)

	assert objs[0].db.adventure_session_id == 1
	for obj in objs[1:]:
		assert not hasattr(obj.db, "adventure_session_id")
	assert expired_sessions == [expired]
	assert counts["adventure_attrs"] == 3


def test_battle_cleanup_tick_reports_stale_cleanup(monkeypatch):
	script = types.SimpleNamespace(db=types.SimpleNamespace())
	context = heartbeat.HeartbeatContext(
		script=script,
		now=datetime(2026, 7, 4, 12, 0, tzinfo=timezone.utc),
	)

	class Handler:
		instances = {7: object()}

	heartbeat_module = types.SimpleNamespace(battle_handler=Handler())
	monkeypatch.setitem(__import__("sys").modules, "pokemon.battle.handler", heartbeat_module)
	monkeypatch.setattr(stale_state, "cleanup_stale_state", lambda active_battle_ids=None: {"battle_id": 1})
	monkeypatch.setattr(stale_state, "format_cleanup_counts", lambda counts: "cleared battle_id=1")

	message = heartbeat.battle_cleanup_tick(context)

	assert "active battles now 1" in message
	assert "cleared battle_id=1" in message

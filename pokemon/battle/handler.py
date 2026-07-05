from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, Dict

from utils.safe_import import safe_import

try:  # pragma: no cover - Evennia logger may be unavailable in tests
	_logger = safe_import("evennia.utils.logger")
	log_info = _logger.log_info  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - fallback if Evennia not available
	import logging

	_log = logging.getLogger(__name__)

	def log_info(*args, **kwargs):
		_log.info(*args, **kwargs)


try:  # pragma: no cover - search requires Evennia runtime
	_evennia = safe_import("evennia")
	search_object = _evennia.search_object  # type: ignore[attr-defined]
	ServerConfig = safe_import("evennia.server.models").ServerConfig  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - fallback stubs when Evennia missing

	def search_object(*args, **kwargs):  # type: ignore[misc]
		return []

	class ServerConfig:  # type: ignore[no-redef]
		class objects:  # pragma: no cover - minimal stub
			@staticmethod
			def conf(key, default=None, value=None, delete=False):
				return default


from .storage import BattleDataWrapper
from .registry import REGISTRY

if TYPE_CHECKING:
	from .battleinstance import BattleSession


class BattleHandler:
	"""Track and persist active battle instances."""

	def __init__(self):
		# map active battle_id -> BattleSession
		self.instances: Dict[int, BattleSession] = {}
		self.ndb = SimpleNamespace(instances=self.instances)
		self._next_id_fallback = 1

	# -------------------------------------------------------------
	# ID generation
	# -------------------------------------------------------------
	def next_id(self) -> int:
		"""Return the next unique battle id."""
		current = self._server_conf("next_battle_id", default=None)
		try:
			current = int(current) if current is not None else int(self._next_id_fallback)
		except (TypeError, ValueError):
			current = int(self._next_id_fallback)
		next_value = current + 1
		self._server_conf(key="next_battle_id", value=next_value)
		self._next_id_fallback = next_value
		return current

	# -------------------------------------------------------------
	# Persistence helpers
	# -------------------------------------------------------------
	def _server_conf(self, key, default=None, value=None, delete=False):
		"""Best-effort wrapper around Evennia ServerConfig persistence."""
		try:
			return ServerConfig.objects.conf(key=key, default=default, value=value, delete=delete)
		except Exception as err:  # pragma: no cover - depends on runtime DB availability
			log_info(f"BattleHandler ServerConfig unavailable for {key}: {err}")
			return default

	def _save(self) -> None:
		"""Persist the current active battle ids and their rooms."""
		data = {bid: inst.room.id for bid, inst in self.instances.items()}
		self._server_conf(key="active_battle_rooms", value=data)

	def restore(self) -> None:
		"""Reload any battle instances stored on the server."""
		mapping = self._server_conf("active_battle_rooms", default={}) or {}
		from .battleinstance import BattleSession

		for bid, rid in mapping.items():
			rooms = search_object(f"#{rid}")
			if not rooms:
				continue
			room = rooms[0]
			try:
				inst = BattleSession.restore(room, int(bid))
			except Exception:
				continue
			if inst:
				self.register(inst)
		self._save()

	def save(self) -> None:
		"""Persist the currently tracked instances."""
		self._save()

	def clear(self) -> None:
		"""Remove all tracked battle instances."""
		for inst in list(self.instances.values()):
			REGISTRY.unregister(inst)
		self.instances.clear()
		self._server_conf(key="active_battle_rooms", delete=True)

	# -------------------------------------------------------------
	# Management API
	# -------------------------------------------------------------
	def get(self, battle_id: int) -> "BattleSession | None":
		"""Return the active session for ``battle_id`` if one is registered."""

		try:
			return self.instances.get(int(battle_id))
		except (TypeError, ValueError):
			return None

	def for_player(self, player) -> "BattleSession | None":
		"""Return the registered session involving ``player`` if any."""

		if not player:
			return None
		ndb_inst = getattr(getattr(player, "ndb", None), "battle_instance", None)
		if ndb_inst is not None and self.get(getattr(ndb_inst, "battle_id", None)) is ndb_inst:
			return ndb_inst

		battle_id = getattr(getattr(player, "db", None), "battle_id", None)
		inst = self.get(battle_id)
		if inst is not None:
			return inst

		player_id = getattr(player, "id", None)
		for candidate in self.instances.values():
			for collection_name in ("teamA", "teamB", "trainers", "observers"):
				collection = getattr(candidate, collection_name, None) or []
				try:
					if player in collection:
						return candidate
					if player_id is not None and any(getattr(obj, "id", None) == player_id for obj in collection):
						return candidate
				except TypeError:
					continue
		return None

	def watch(self, battle_id: int, watcher) -> bool:
		"""Register ``watcher`` on a canonical battle session."""

		inst = self.get(battle_id)
		if not inst:
			return False
		add = getattr(inst, "add_observer", None) or getattr(inst, "add_watcher", None)
		if callable(add):
			add(watcher)
			return True
		return False

	def unwatch(self, battle_id: int, watcher) -> bool:
		"""Remove ``watcher`` from a canonical battle session."""

		inst = self.get(battle_id)
		if not inst:
			return False
		remove = getattr(inst, "remove_observer", None) or getattr(inst, "remove_watcher", None)
		if callable(remove):
			remove(watcher)
			return True
		return False

	def abort(self, battle_id: int) -> None:
		"""End a canonical battle session if it is registered."""

		inst = self.get(battle_id)
		if not inst:
			return
		end = getattr(inst, "end", None)
		if callable(end):
			end()
		else:
			self.unregister(inst)

	def abort_request(self, battle_id: int, requester) -> bool:
		"""Compatibility hook for older battle-manager callers."""

		inst = self.get(battle_id)
		if not inst:
			return False
		message = f"{getattr(requester, 'key', requester)} aborts battle #{battle_id}."
		notify = getattr(inst, "notify", None) or getattr(inst, "msg", None)
		if callable(notify):
			try:
				notify(message)
			except Exception:
				pass
		self.abort(battle_id)
		return True

	def register(self, inst: BattleSession) -> None:
		"""Track the given battle session."""
		if not inst:
			return
		self.instances[inst.battle_id] = inst
		REGISTRY.register(inst)
		self._save()

	def unregister(self, inst: BattleSession) -> None:
		if not inst:
			return
		bid = inst.battle_id
		REGISTRY.unregister(inst)
		if bid in self.instances:
			del self.instances[bid]
			self._save()

	# -------------------------------------------------------------
	# Reload helpers
	# -------------------------------------------------------------
	def rebuild_ndb(self) -> None:
		"""Repopulate ndb attributes for all tracked battle instances."""

		log_info(f"Rebuilding ndb data for {len(self.instances)} active battles")
		for inst in list(self.instances.values()):
			battle_instances = getattr(inst.room.ndb, "battle_instances", None)
			if not battle_instances or not hasattr(battle_instances, "__setitem__"):
				battle_instances = {}
				inst.room.ndb.battle_instances = battle_instances
			battle_instances[inst.battle_id] = inst

			room_key = getattr(inst.room, "key", inst.room.id)
			log_info(f"Restored battle {inst.battle_id} in room '{room_key}' (#{inst.room.id})")

			# rebuild live logic from stored room data if needed
			if not inst.logic:
				storage = BattleDataWrapper(inst.room, inst.battle_id)
				data = storage.get("data")
				state = storage.get("state")
				if data is not None or state is not None or storage.get("logic") is not None:
					from .battleinstance import BattleLogic

					if data is None or state is None:
						logic_info = storage.get("logic", {}) or {}
						data = data or logic_info.get("data")
						state = state or logic_info.get("state")
					inst.logic = BattleLogic.from_dict({"data": data, "state": state})
					inst.logic.battle.log_action = inst.notify
					inst.temp_pokemon_ids = list(storage.get("temp_pokemon_ids") or [])
				inst.storage = storage

			for obj in inst.trainers + list(inst.observers):
				if obj:
					obj.ndb.battle_instance = inst

			# expose battle info on the captains after the ndb rebuild
			try:
				if inst.captainA:
					inst.captainA.team = [p for p in inst.logic.data.teams["A"].returnlist() if p]
					part_a = inst.logic.battle.participants[0]
					if part_a.active:
						inst.captainA.active_pokemon = part_a.active[0]
				if inst.captainB:
					inst.captainB.team = [p for p in inst.logic.data.teams["B"].returnlist() if p]
					if len(inst.logic.battle.participants) > 1:
						part_b = inst.logic.battle.participants[1]
						if part_b.active:
							inst.captainB.active_pokemon = part_b.active[0]

				# Reattach participant -> player references
				parts = getattr(inst.logic.battle, "participants", [])
				team_map = {"A": inst.teamA, "B": inst.teamB}
				team_idx = {"A": 0, "B": 0}
				for part in parts:
					t = getattr(part, "team", None)
					if t in team_map:
						idx = team_idx.get(t, 0)
						if idx < len(team_map[t]):
							part.player = team_map[t][idx]
						team_idx[t] = idx + 1
			except Exception:
				# Logic may be incomplete; fail silently
				pass

			# ensure trainer list reflects current captains
			if inst.captainA or inst.captainB:
				inst.trainers = [t for t in (inst.captainA, inst.captainB) if t]
			else:
				inst.trainers = []


battle_handler = BattleHandler()

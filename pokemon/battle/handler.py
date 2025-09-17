from __future__ import annotations

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

	# -------------------------------------------------------------
	# ID generation
	# -------------------------------------------------------------
	def next_id(self) -> int:
		"""Return the next unique battle id."""
		current = ServerConfig.objects.conf("next_battle_id", default=1)
		ServerConfig.objects.conf(key="next_battle_id", value=current + 1)
		return current

	# -------------------------------------------------------------
	# Persistence helpers
	# -------------------------------------------------------------
	def _save(self) -> None:
		"""Persist the current active battle ids and their rooms."""
		data = {bid: inst.room.id for bid, inst in self.instances.items()}
		ServerConfig.objects.conf(key="active_battle_rooms", value=data)

	def restore(self) -> None:
		"""Reload any battle instances stored on the server."""
		mapping = ServerConfig.objects.conf("active_battle_rooms", default={})
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
		ServerConfig.objects.conf(key="active_battle_rooms", delete=True)

	# -------------------------------------------------------------
	# Management API
	# -------------------------------------------------------------
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

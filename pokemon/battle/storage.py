"""Utility for storing per-battle data on rooms."""

from __future__ import annotations


class BattleDataWrapper:
	"""Helper to read and write battle data parts on a room."""

	def __init__(self, room, battle_id: int) -> None:
		self.room = room
		self.battle_id = battle_id

	def _key(self, part: str) -> str:
		return f"battle_{self.battle_id}_{part}"

	def get(self, part: str, default=None):
		"""Return the stored value for ``part`` or ``default``."""
		return getattr(self.room.db, self._key(part), default)

	def set(self, part: str, value) -> None:
		"""Store ``value`` for ``part`` on the room."""
		setattr(self.room.db, self._key(part), value)

	def delete(self, part: str) -> None:
		"""Remove stored ``part`` if present."""
		key = self._key(part)
		if hasattr(self.room.db, key):
			delattr(self.room.db, key)


__all__ = ["BattleDataWrapper"]

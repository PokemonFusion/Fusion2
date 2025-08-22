"""Command to inspect resolved move data from the dex."""

from evennia import Command

from pokemon.battle.engine import BattleMove, _normalize_key
from pokemon.dex import MOVEDEX


class CmdDebugMoveData(Command):
	"""Display resolved move data for debugging.

	Usage:
	  +debug/movedata <move>
	"""

	key = "+debug/movedata"
	locks = "cmd:all()"
	help_category = "Pokemon"

	def func(self):  # type: ignore[override]
		name = (self.args or "").strip()
		if not name:
			self.caller.msg("Usage: +debug/movedata <move>")
			return

		move_obj = BattleMove(name)
		key = getattr(move_obj, "key", _normalize_key(name))
		dex_move = MOVEDEX.get(key)
		if not dex_move:
			self.caller.msg("Move not found.")
			return

		raw = getattr(dex_move, "raw", {}) or {}
		if not move_obj.raw:
			move_obj.raw = dict(raw)

		if move_obj.power in (None, 0):
			bp = raw.get("basePower")
			if isinstance(bp, (int, float)) and bp > 0:
				move_obj.power = int(bp)
			else:
				dm_pow = getattr(dex_move, "power", None)
				if isinstance(dm_pow, (int, float)) and dm_pow not in (None, 0):
					move_obj.power = int(dm_pow)

		acc = raw.get("accuracy", getattr(dex_move, "accuracy", None))
		if acc is not None:
			move_obj.accuracy = acc

		if move_obj.type is None:
			move_obj.type = getattr(dex_move, "type", raw.get("type"))
		if move_obj.priority == 0:
			move_obj.priority = int(raw.get("priority", 0))

		msg = (
			f"key={move_obj.key} power={move_obj.power} accuracy={move_obj.accuracy} "
			f"type={move_obj.type} priority={move_obj.priority}"
		)
		self.caller.msg(msg)

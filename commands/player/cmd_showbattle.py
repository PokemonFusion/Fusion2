"""Command to show ongoing battle interfaces."""
from __future__ import annotations

try:
	from evennia import Command, search_object
	if Command is None:
		raise ImportError
except Exception:
	class Command: pass
	def search_object(*args, **kwargs):
		return []

from pokemon.battle.interface import display_battle_interface


class CmdShowBattle(Command):
	"""Show your current battle or another character's battle.

	Usage:
	  +showbattle
	  +showbattle <character>
	"""

	key = "+showbattle"
	aliases = ["+battleview", "+battleui"]
	locks = "cmd:all()"
	help_category = "Pokemon"

	def func(self):
		target = self.caller
		if self.args:
			name = self.args.strip()
			results = search_object(name)
			if not results:
				self.caller.msg("No such character.")
				return
			target = results[0]

		inst = getattr(target.ndb, "battle_instance", None)
		if not inst or not getattr(inst, "state", None):
			self.caller.msg("They are not currently in battle.")
			return

		viewer_team = None
		if target in getattr(inst, "teamA", []):
			viewer_team = "A"
		elif target in getattr(inst, "teamB", []):
			viewer_team = "B"

		ui = display_battle_interface(
			inst.captainA,
			inst.captainB,
			inst.state,
			viewer_team=viewer_team,
		)
		self.caller.msg(ui)

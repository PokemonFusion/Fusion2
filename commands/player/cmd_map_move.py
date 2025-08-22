"""Command allowing movement within the current map."""

from evennia import Command


class CmdMapMove(Command):
	"""Move inside the current map.

	Usage:
	  @mapmove <n|s|e|w>
	"""

	key = "@mapmove"
	locks = "cmd:all()"
	help_category = "General"

	def func(self):
		dir_map = {"n": (0, -1), "s": (0, 1), "e": (1, 0), "w": (-1, 0)}
		direction = self.args.strip().lower()
		if direction not in dir_map:
			self.caller.msg("Choose a direction: n, s, e, w")
			return

		location = self.caller.location
		if not location or not hasattr(location, "move_entity"):
			self.caller.msg("You're not in a grid map room.")
			return

		dx, dy = dir_map[direction]
		location.move_entity(self.caller, dx, dy)

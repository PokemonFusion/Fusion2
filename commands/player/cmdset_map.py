from evennia import CmdSet

from .cmd_map_move import CmdMapMove
from .cmdstartmap import CmdStartMap, map_prototype_enabled


class MapCmdSet(CmdSet):
	key = "MapCmdSet"

	def at_cmdset_creation(self):
		if not map_prototype_enabled():
			return
		self.add(CmdMapMove())
		self.add(CmdStartMap())

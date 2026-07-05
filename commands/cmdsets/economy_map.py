"""CmdSet for economy and map related commands."""

from evennia import CmdSet

from commands.player.cmd_map_move import CmdMapMove
from commands.player.cmd_pokestore import CmdPokestore
from commands.player.cmd_store import CmdStore
from commands.player.cmdstartmap import CmdStartMap, map_prototype_enabled


class EconomyMapCmdSet(CmdSet):
	"""CmdSet combining economy and world map commands."""

	key = "EconomyMapCmdSet"

	def at_cmdset_creation(self):
		"""Populate the cmdset."""
		cmds = [CmdStore, CmdPokestore]
		if map_prototype_enabled():
			cmds.extend([CmdMapMove, CmdStartMap])
		for cmd in cmds:
			self.add(cmd())

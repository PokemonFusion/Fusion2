"""CmdSet for Pokédex lookup commands."""

from evennia import CmdSet

from commands.player.cmd_pokedex import (
	CmdItemdexSearch,
	CmdMovedexSearch,
	CmdMovesetSearch,
	CmdPokedexAll,
	CmdPokedexNumber,
	CmdPokedexSearch,
	CmdStarterList,
)


class PokedexCmdSet(CmdSet):
	"""CmdSet containing commands querying Pokédex data."""

	key = "PokedexCmdSet"

	def at_cmdset_creation(self):
		"""Populate the cmdset."""
		for cmd in (
			CmdPokedexSearch,
			CmdPokedexAll,
			CmdItemdexSearch,
			CmdMovedexSearch,
			CmdMovesetSearch,
			CmdPokedexNumber,
			CmdStarterList,
		):
			self.add(cmd())

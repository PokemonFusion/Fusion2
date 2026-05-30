from evennia import Command

import menus.pokestore as pokestore
from utils.enhanced_evmenu import EnhancedEvMenu


class CmdPokestore(Command):
	"""Access Pokémon storage at a Pokémon Center.

	Usage:
	  +pokestore
	"""

	key = "+pokestore"
	locks = "cmd:all()"
	help_category = "Pokemon"

	def func(self):
		if not (self.caller.location and self.caller.location.db.is_pokemon_center):
			self.caller.msg("You must be at a Pokémon Center to access storage.")
			return
		EnhancedEvMenu(self.caller, pokestore, startnode="node_start", cmd_on_exit=None)

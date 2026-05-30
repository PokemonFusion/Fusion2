from evennia import Command

import menus.pokestore as pokestore
from utils.enhanced_evmenu import EnhancedEvMenu


class CmdPokestore(Command):
    """Open interactive Pokemon storage at a Pokemon Center.

    Usage:
      +storage

    Examples:
      +storage

    Notes:
      Use +box when you only need to view a storage box.
    """

    key = "+storage"
    aliases = ["+pokestore", "pokestore"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        if not (self.caller.location and self.caller.location.db.is_pokemon_center):
            self.caller.msg("You must be at a Pokémon Center to access storage.")
            return
        EnhancedEvMenu(self.caller, pokestore, startnode="node_start", cmd_on_exit=None)

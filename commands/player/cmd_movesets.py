from evennia import Command

import menus.moveset_manager as moveset_manager
from utils.enhanced_evmenu import EnhancedEvMenu


class CmdMovesets(Command):
    """Manage saved movesets at a Pokemon Center.

    Usage:
      +movesets

    Examples:
      +movesets

    Notes:
      Use +moves/use <slot>=<set#> to switch a Pokemon to one of these sets.
    """

    key = "+movesets"
    aliases = ["movesets"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        caller = self.caller
        if not (caller.location and caller.location.db.is_pokemon_center):
            caller.msg("You must be at a Pokémon Center to manage movesets.")
            return
        EnhancedEvMenu(caller, moveset_manager, startnode="node_start", cmd_on_exit=None)

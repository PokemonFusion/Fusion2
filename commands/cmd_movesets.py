from evennia import Command
from pokemon.utils.enhanced_evmenu import EnhancedEvMenu
import menus.moveset_manager as moveset_manager


class CmdMovesets(Command):
    """Manage stored movesets at a Pokémon Center."""

    key = "movesets"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        EnhancedEvMenu(self.caller, moveset_manager, startnode="node_start", cmd_on_exit=None)


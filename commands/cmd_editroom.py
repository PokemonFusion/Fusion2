from evennia import Command
from pokemon.utils.enhanced_evmenu import EnhancedEvMenu
import menus.edit_room as edit_room

class CmdEditRoom(Command):
    """Interactive wizard for editing rooms.

    Usage:
      @editroom
    """

    key = "@editroom"
    locks = "cmd:perm(Builders)"
    help_category = "Building"

    def func(self):
        EnhancedEvMenu(
            self.caller,
            edit_room,
            startnode="node_start",
            cmd_on_exit="look",
        )


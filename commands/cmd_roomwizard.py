from evennia import Command
from pokemon.utils.enhanced_evmenu import EnhancedEvMenu
import menus.room_wizard as room_wizard

class CmdRoomWizard(Command):
    """
    Interactive wizard for creating rooms.

    Usage:
      @roomwizard
    """
    key = "@roomwizard"
    locks = "cmd:perm(Builders)"
    help_category = "Building"

    def func(self):
        EnhancedEvMenu(
            self.caller,
            room_wizard,
            startnode="node_start",
            cmd_on_exit="look",
        )

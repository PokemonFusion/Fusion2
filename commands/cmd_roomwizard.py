from evennia import Command
from evennia.utils.evmenu import EvMenu
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
        EvMenu(
            self.caller,
            room_wizard,
            cmd_on_exit=True
        )

from evennia import Command
from evennia.utils.evmenu import EvMenu
import menus.edit_room as edit_room

class CmdEditRoom(Command):
    """Interactive wizard for editing rooms."""

    key = "@editroom"
    locks = "cmd:perm(Builders)"
    help_category = "Building"

    def func(self):
        EvMenu(self.caller, edit_room, startnode="node_start", cmd_on_exit=True)


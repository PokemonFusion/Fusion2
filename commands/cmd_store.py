from evennia import Command
from evennia.utils.evmenu import EvMenu
import menus.item_store as item_store


class CmdStore(Command):
    """Access the item store in the current room."""

    key = "store"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        if not self.caller.location or not self.caller.location.db.is_item_shop:
            self.caller.msg("There is no store here.")
            return
        EvMenu(self.caller, item_store, startnode="node_start", cmd_on_exit=None)


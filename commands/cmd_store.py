from evennia import Command
from helpers.enhanced_evmenu import EnhancedEvMenu
import menus.item_store as item_store


class CmdStore(Command):
    """Access the item store in the current room.

    Usage:
      store
    """

    key = "store"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        if not self.caller.location or not self.caller.location.db.is_item_shop:
            self.caller.msg("There is no store here.")
            return
        EnhancedEvMenu(self.caller, item_store, startnode="node_start", cmd_on_exit=None)


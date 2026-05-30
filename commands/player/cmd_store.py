from evennia import Command

import menus.item_store as item_store
from utils.enhanced_evmenu import EnhancedEvMenu


class CmdStore(Command):
    """Access the item store in the current room.

    Usage:
      +store

    Examples:
      +store

    Notes:
      This only works in rooms configured as item shops.
    """

    key = "+store"
    aliases = ["store"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        if not self.caller.location or not self.caller.location.db.is_item_shop:
            self.caller.msg("There is no store here.")
            return
        EnhancedEvMenu(self.caller, item_store, startnode="node_start", cmd_on_exit=None)

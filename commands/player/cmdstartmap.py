from evennia import Command

from world import maphandler


class CmdStartMap(Command):
    """Start a map instance for solo adventuring.

    Usage:
      +map/start

    Examples:
      +map/start

    Notes:
      This creates a temporary solo map instance for your character.
    """

    key = "+map/start"
    aliases = ["@startmap"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        room = maphandler.create_map_instance(self.caller)
        self.caller.msg(f"Entering map instance: {room.key}")

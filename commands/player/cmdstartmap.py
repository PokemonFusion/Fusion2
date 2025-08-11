from evennia import Command
from world import maphandler


class CmdStartMap(Command):
    """Start a map instance for solo adventuring.

    Usage:
      @startmap
    """

    key = "@startmap"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        room = maphandler.create_map_instance(self.caller)
        self.caller.msg(f"Entering map instance: {room.key}")

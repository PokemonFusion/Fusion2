from evennia import Command
from world import maphandler


class CmdStartMap(Command):
    """Start a map instance for solo adventuring."""

    key = "@startmap"
    locks = "cmd:all()"

    def func(self):
        room = maphandler.create_map_instance(self.caller)
        self.caller.msg(f"Entering map instance: {room.key}")

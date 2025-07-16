"""Command for attempting to hunt wild Pokémon."""
from __future__ import annotations

from evennia import Command

from world.hunt_system import HuntSystem


class CmdHunt(Command):
    """Attempt to encounter a wild Pokémon in the current room.

    Usage:
      +hunt
    """

    key = "+hunt"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        system = HuntSystem(self.obj.location)
        result = system.perform_hunt(self.caller)
        self.caller.msg(result)


class CmdLeaveHunt(Command):
    """Leave a hunting instance.

    Usage:
      +leave
    """

    key = "+leave"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        room = self.caller.ndb.get("hunt_room")
        if not room:
            self.caller.msg("You are not hunting.")
            return
        self.caller.move_to(room.home or self.caller.home, quiet=True)
        room.delete()
        del self.caller.ndb.hunt_room
        self.caller.msg("You stop hunting.")


class CmdCustomHunt(Command):
    """Start a hunt with a specified Pokémon and level.

    Usage:
      +huntcustom <pokemon> <level>
    """

    key = "+huntcustom"
    locks = "cmd:perm(Builders)"
    help_category = "Admin"

    def func(self):
        parts = self.args.split()
        if len(parts) != 2:
            self.caller.msg("Usage: +huntcustom <pokemon> <level>")
            return

        name = parts[0]
        try:
            level = int(parts[1])
        except ValueError:
            self.caller.msg("Level must be a number.")
            return

        system = HuntSystem(self.obj.location)
        result = system.perform_fixed_hunt(self.caller, name, level)
        self.caller.msg(result)

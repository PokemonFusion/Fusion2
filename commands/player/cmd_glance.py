from evennia import Command
from evennia.objects.objects import DefaultCharacter
from evennia.utils import utils
from evennia.utils.evtable import EvTable


class CmdGlance(Command):
    """Show a brief overview of online characters in the room.

    Usage:
      +glance
    """

    key = "+glance"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        location = caller.location
        if not location:
            caller.msg("You have no location to glance at.")
            return

        chars = []
        for obj in location.contents:
            if not obj.is_typeclass(DefaultCharacter, exact=False):
                continue
            if not obj.sessions.all():
                continue
            chars.append(obj)

        if not chars:
            caller.msg("No online characters here.")
            return

        table = EvTable("Name", "Gender", "Species", "Idle")
        for char in chars:
            gender = char.db.gender or "Unknown"
            species = char.db.fusion_species or "Human"
            idle = char.idle_time
            idle_str = utils.time_format(idle, 1) if idle is not None else "0s"
            table.add_row(char.key, gender, species, idle_str)

        caller.msg(str(table))

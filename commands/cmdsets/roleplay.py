"""CmdSet grouping roleplay related commands."""

from evennia import CmdSet
from commands.cmd_roleplay import CmdGOIC, CmdGOOOC, CmdOOC
from commands.cmd_glance import CmdGlance
from commands.command import CmdSpoof


class RoleplayCmdSet(CmdSet):
    """CmdSet with commands aiding roleplay."""

    key = "RoleplayCmdSet"

    def at_cmdset_creation(self):
        """Populate the cmdset."""
        self.add(CmdSpoof())
        self.add(CmdGlance())
        self.add(CmdOOC())

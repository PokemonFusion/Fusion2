"""CmdSet grouping roleplay related commands."""

from evennia import CmdSet
from commands.player.cmd_roleplay import CmdGOIC, CmdGOOOC, CmdOOC
from commands.player.cmd_glance import CmdGlance
from commands.debug.command import CmdSpoof


class RoleplayCmdSet(CmdSet):
    """CmdSet with commands aiding roleplay."""

    key = "RoleplayCmdSet"

    def at_cmdset_creation(self):
        """Populate the cmdset."""
        self.add(CmdSpoof())
        self.add(CmdGlance())
        self.add(CmdOOC())

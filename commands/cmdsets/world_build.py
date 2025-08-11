"""CmdSet for world building and administration commands."""

from evennia import CmdSet
from commands.cmd_chargen import CmdChargen
from commands.cmd_roomwizard import CmdRoomWizard
from commands.cmd_editroom import CmdEditRoom
from commands.cmd_validate import CmdValidate
from commands.cmd_spawns import CmdSpawns


class WorldBuildCmdSet(CmdSet):
    """CmdSet containing commands used for building the world."""

    key = "WorldBuildCmdSet"

    def at_cmdset_creation(self):
        """Populate the cmdset."""
        for cmd in (CmdChargen, CmdRoomWizard, CmdEditRoom, CmdValidate, CmdSpawns):
            self.add(cmd())

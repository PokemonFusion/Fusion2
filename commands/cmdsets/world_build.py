"""CmdSet for world building and administration commands."""

from evennia import CmdSet
from commands.player.cmd_chargen import CmdChargen
from commands.admin.cmd_roomwizard import CmdRoomWizard
from commands.admin.cmd_editroom import CmdEditRoom
from commands.admin.cmd_validate import CmdValidate
from commands.admin.cmd_spawns import CmdSpawns


class WorldBuildCmdSet(CmdSet):
    """CmdSet containing commands used for building the world."""

    key = "WorldBuildCmdSet"

    def at_cmdset_creation(self):
        """Populate the cmdset."""
        for cmd in (CmdChargen, CmdRoomWizard, CmdEditRoom, CmdValidate, CmdSpawns):
            self.add(cmd())

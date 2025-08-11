"""CmdSet for player-vs-player battle commands."""

from evennia import CmdSet
from commands.player.cmd_pvp import (
    CmdPvpHelp,
    CmdPvpList,
    CmdPvpCreate,
    CmdPvpJoin,
    CmdPvpAbort,
    CmdPvpStart,
)


class PvpCmdSet(CmdSet):
    """CmdSet with PvP-related commands."""

    key = "PvpCmdSet"

    def at_cmdset_creation(self):
        """Populate the cmdset."""
        for cmd in (
            CmdPvpHelp,
            CmdPvpList,
            CmdPvpCreate,
            CmdPvpJoin,
            CmdPvpAbort,
            CmdPvpStart,
        ):
            self.add(cmd())

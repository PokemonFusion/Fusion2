"""CmdSet grouping bulletin board commands."""

from evennia import CmdSet

from bboard.commands import (
    CmdBBDelete,
    CmdBBEdit,
    CmdBBList,
    CmdBBLock,
    CmdBBMove,
    CmdBBNew,
    CmdBBPost,
    CmdBBPurge,
    CmdBBRead,
    CmdBBSet,
)


class BulletinBoardCmdSet(CmdSet):
    """CmdSet containing bulletin board related commands."""

    key = "BulletinBoardCmdSet"

    def at_cmdset_creation(self):
        """Populate the cmdset."""
        self.add(CmdBBList())
        self.add(CmdBBRead())
        self.add(CmdBBPost())
        self.add(CmdBBDelete())
        self.add(CmdBBSet())
        self.add(CmdBBNew())
        self.add(CmdBBEdit())
        self.add(CmdBBMove())
        self.add(CmdBBPurge())
        self.add(CmdBBLock())

"""CmdSet grouping bulletin board commands."""

from evennia import CmdSet

from bboard.commands import (
	CmdBBCatchup,
	CmdBBDelete,
	CmdBBEdit,
	CmdBBHelp,
	CmdBBList,
	CmdBBLock,
	CmdBBMove,
	CmdBBNew,
	CmdBBNext,
	CmdBBPost,
	CmdBBPurge,
	CmdBBRead,
	CmdBBSeed,
	CmdBBSet,
)


class BulletinBoardCmdSet(CmdSet):
	"""CmdSet containing bulletin board related commands."""

	key = "BulletinBoardCmdSet"

	def at_cmdset_creation(self):
		"""Populate the cmdset."""
		self.add(CmdBBHelp())
		self.add(CmdBBList())
		self.add(CmdBBRead())
		self.add(CmdBBPost())
		self.add(CmdBBDelete())
		self.add(CmdBBCatchup())
		self.add(CmdBBNext())
		self.add(CmdBBSet())
		self.add(CmdBBNew())
		self.add(CmdBBSeed())
		self.add(CmdBBEdit())
		self.add(CmdBBMove())
		self.add(CmdBBPurge())
		self.add(CmdBBLock())

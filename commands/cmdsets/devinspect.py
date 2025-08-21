from __future__ import annotations

"""CmdSet providing developer inspection and test utilities."""

from evennia import CmdSet, Command

from ..admin.cmd_battleinspect import CmdBattleInspect


class CmdToggleDevInspect(Command):
	"""@toggleinspect
	Toggle developer inspection and test cmdsets on the caller."""

	key = "@toggleinspect"
	aliases = ["toggleinspect"]
	locks = "cmd:perm(Developers) or perm(Admin) or perm(Builder)"
	help_category = "Admin"

	def func(self):  # type: ignore[override]
		"""Add or remove ``DevInspectCmdSet`` and ``TestCmdSet``."""

		from commands.cmdsets.test import TestCmdSet

		has_dev = self.caller.cmdset.has_cmdset(DevInspectCmdSet, must_be_default=False)
		has_test = self.caller.cmdset.has_cmdset(TestCmdSet, must_be_default=False)
		if has_dev or has_test:
			if has_dev:
				self.caller.cmdset.delete(DevInspectCmdSet)
			if has_test:
				self.caller.cmdset.delete(TestCmdSet)
			self.msg("Dev/test cmdsets |rremoved|n.")
		else:
			self.caller.cmdset.add(DevInspectCmdSet, persistent=False)
			self.caller.cmdset.add(TestCmdSet, persistent=False)
			self.msg("Dev/test cmdsets |gadded|n. Use |Wbattleinspect|n.")


class DevInspectCmdSet(CmdSet):
	"""CmdSet bundling developer inspection commands."""

	key = "DevInspectCmdSet"
	priority = 110
	mergetype = "Replace"

	def at_cmdset_creation(self):
		"""Populate the cmdset."""

		self.add(CmdBattleInspect())
		self.add(CmdToggleDevInspect())

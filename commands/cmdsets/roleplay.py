"""CmdSet grouping roleplay related commands."""

from evennia import CmdSet

from commands.debug.command import CmdNoSpoof, CmdSpoof
from commands.player.cmd_glance import CmdGlance
from commands.player.cmd_profile import CmdProfile
from commands.player.cmd_roleplay import CmdOOC
from commands.player.cmd_where import CmdWhere
from commands.player.cmd_who import CmdWho


class RoleplayCmdSet(CmdSet):
	"""CmdSet with commands aiding roleplay."""

	key = "RoleplayCmdSet"

	def at_cmdset_creation(self):
		"""Populate the cmdset."""
		self.add(CmdSpoof())
		self.add(CmdNoSpoof())
		self.add(CmdGlance())
		self.add(CmdWhere())
		self.add(CmdWho())
		self.add(CmdProfile())
		self.add(CmdOOC())

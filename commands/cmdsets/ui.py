"""CmdSet for user interface related commands."""

from evennia import CmdSet

from commands.player.cmd_uimode import CmdUiMode
from commands.player.cmd_uitheme import CmdUiTheme


class UiCmdSet(CmdSet):
	"""CmdSet containing UI helper commands."""

	key = "UiCmdSet"

	def at_cmdset_creation(self):
		"""Populate the cmdset."""
		self.add(CmdUiMode())
		self.add(CmdUiTheme())

"""Command set for dev-only battle testing."""

from evennia import CmdSet

from ..debug.devtest import CmdTestBattle, CmdToggleTest


class DevTestCmdSet(CmdSet):
	"""Dev-only commands for rapid battle testing.
	Attach/detach via ``@toggletest``.
	"""

	key = "DevTestCmdSet"
	priority = 110  # higher than default player cmdsets

	def at_cmdset_creation(self):
		self.add(CmdToggleTest())
		self.add(CmdTestBattle())

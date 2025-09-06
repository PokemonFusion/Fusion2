"""CmdSet for developer commands overriding @py to use a fixed console."""

from evennia.commands.default.cmdset_account import CharacterCmdSet as DefaultCharacterCmdSet
from fusion2.commands.admin.cmd_py_fixed import CmdPy as CmdPyFixed


class DevCmdSet(DefaultCharacterCmdSet):
	"""CmdSet including the patched @py command."""

	key = "DevCmdSet"
	priority = 1
	merge_type = "Union"

	def at_cmdset_creation(self):
		"""Populate the command set."""
		super().at_cmdset_creation()
		# Override stock @py with our fixed version
		self.add(CmdPyFixed())

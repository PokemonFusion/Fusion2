"""Command to launch the EnhancedEvMenu sanity-check."""

from evennia import Command

from menus import evmenu_sanity
from utils.enhanced_evmenu import EnhancedEvMenu


class CmdTestMenuEnhanced(Command):
	"""
	Launch the EnhancedEvMenu sanity-check.

	Usage:
	    testmenu+enh
	    testmenu+enh persistent
	"""

	key = "testmenu+enh"
	locks = "cmd:all()"

	def func(self):
		persistent = "persistent" in (self.args or "").lower()
		EnhancedEvMenu(
			self.caller,
			evmenu_sanity,
			startnode="node_start",
			auto_quit=True,
			persistent=persistent,
			cmd_on_exit="look",
		)

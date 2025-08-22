from __future__ import annotations

from evennia import Command

from menus import chargen as chargen_menu
from utils.enhanced_evmenu import EnhancedEvMenu


class CmdChargen(Command):
	"""Interactive character creation.

	Usage:
	  chargen
	"""

	key = "chargen"
	locks = "cmd:all()"
	help_category = "General"

	def func(self):
		if self.caller.db.validated:
			self.caller.msg("You are already validated and cannot run chargen again.")
			return
		EnhancedEvMenu(
			self.caller,
			chargen_menu,
			startnode="start",
			cmd_on_exit=None,
			on_abort=lambda caller: caller.msg("Character generation aborted."),
			invalid_message="Invalid entry.\nTry again.",
			numbered_options=False,
			show_options=False,
		)

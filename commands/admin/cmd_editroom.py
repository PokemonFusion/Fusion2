from evennia import Command

import menus.edit_room as edit_room
from utils.enhanced_evmenu import EnhancedEvMenu


class CmdEditRoom(Command):
	"""Interactive wizard for editing rooms.

	Usage:
	  @editroom
	"""

	key = "@editroom"
	locks = "cmd:perm(Builders)"
	help_category = "Building"

	def func(self):
		EnhancedEvMenu(
			self.caller,
			edit_room,
			startnode="node_start",
			cmd_on_exit="look",
		)

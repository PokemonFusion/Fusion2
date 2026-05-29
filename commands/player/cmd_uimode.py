from evennia import Command


class CmdUiMode(Command):
	"""Change how room descriptions are displayed.

	Usage:
	  +uimode <fancy|simple|boxed|screenreader>

	Switch between different visual modes for room descriptions.
	"""

	key = "+uimode"
	locks = "cmd:all()"
	help_category = "General"

	def func(self):
		caller = self.caller
		arg = (self.args or "").strip().lower()
		if not arg:
			current = getattr(caller.db, "ui_mode", "fancy")
			pretty = {
				"fancy": "fancy",
				"simple": "simple",
				"boxed": "boxed",
				"sr": "screenreader",
			}.get(current, current)
			caller.msg(f"Current UI mode: {pretty}.")
			return

		mapping = {
			"fancy": "fancy",
			"simple": "simple",
			"boxed": "boxed",
			"screen": "sr",
			"screenreader": "sr",
			"sr": "sr",
		}
		mode = mapping.get(arg)
		if not mode:
			caller.msg("Usage: +uimode <fancy|simple|boxed|screenreader>")
			return
		caller.db.ui_mode = mode
		pretty = "screenreader" if mode == "sr" else mode
		caller.msg(f"UI mode set to {pretty}.")

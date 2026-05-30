from evennia import Command


class CmdUiTheme(Command):
	"""Change the color theme used for room descriptions.

	Usage:
	  +uitheme [green|blue|red|magenta|cyan|white]

	Without an argument, show the current theme.
	"""

	key = "+uitheme"
	locks = "cmd:all()"
	help_category = "General"

	THEMES = {"green", "blue", "red", "magenta", "cyan", "white"}

	def func(self):
		caller = self.caller
		arg = (self.args or "").strip().lower()
		if not arg:
			current = getattr(caller.db, "ui_theme", "green")
			caller.msg(f"Current UI theme: {current}.")
			return
		if arg not in self.THEMES:
			caller.msg("Usage: +uitheme <green|blue|red|magenta|cyan|white>")
			return
		caller.db.ui_theme = arg
		caller.msg(f"UI theme set to {arg}.")

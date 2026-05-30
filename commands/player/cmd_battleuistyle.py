"""Command for selecting the battle UI renderer style."""

from evennia import Command

from pokemon.ui.battle_render import (
	BATTLE_UI_STYLES,
	DEFAULT_BATTLE_UI_STYLE,
	normalize_battle_ui_style,
)


class CmdBattleUiStyle(Command):
	"""Change your battle interface renderer.

	Usage: +battleuistyle [legacy|classic_modern|pf1]
	"""

	key = "+battleuistyle"
	aliases = ["+battleui/style", "+buistyle"]
	locks = "cmd:all()"
	help_category = "Pokemon"

	def func(self):
		caller = self.caller
		arg = (self.args or "").strip().lower()
		if not arg:
			current = normalize_battle_ui_style(
				getattr(getattr(caller, "db", None), "battle_ui_style", None)
			)
			caller.msg(
				f"Current battle UI style: {current}. Options: {', '.join(BATTLE_UI_STYLES)}."
			)
			return

		style = normalize_battle_ui_style(arg, default=None)
		if style is None or style not in BATTLE_UI_STYLES:
			caller.msg(f"Usage: +battleuistyle <{'|'.join(BATTLE_UI_STYLES)}>")
			return

		if style == DEFAULT_BATTLE_UI_STYLE:
			try:
				delattr(caller.db, "battle_ui_style")
			except Exception:
				caller.db.battle_ui_style = style
		else:
			caller.db.battle_ui_style = style
		caller.msg(f"Battle UI style set to {style}.")

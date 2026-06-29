from evennia import Command


class CmdUiMode(Command):
    """Change how room descriptions are displayed.

    Usage:
      +uimode <fancy||simple||boxed||screenreader||ascii||unicode>

    Examples:
      +uimode
      +uimode screenreader
      +uimode ascii

    Notes:
      With no argument, the command shows your current mode.
      The ascii option uses the simple room layout and ASCII battle symbols.
      The unicode option uses the fancy room layout and Unicode battle symbols.
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
            ascii_symbols = getattr(caller.db, "battle_ascii_symbols", None)
            if ascii_symbols is None:
                ascii_status = "auto"
            elif isinstance(ascii_symbols, str):
                ascii_status = (
                    "on"
                    if ascii_symbols.strip().lower() in ("1", "true", "yes", "on")
                    else "off"
                )
            else:
                ascii_status = "on" if ascii_symbols else "off"
            caller.msg(f"Current UI mode: {pretty}. ASCII symbols: {ascii_status}.")
            return

        mapping = {
            "fancy": "fancy",
            "simple": "simple",
            "boxed": "boxed",
            "screen": "sr",
            "screenreader": "sr",
            "sr": "sr",
        }
        if arg in ("ascii", "ascii-safe", "ascii_safe"):
            caller.db.ui_mode = "simple"
            caller.db.battle_ascii_symbols = True
            caller.msg(
                "UI mode set to ascii-safe. Room display uses simple layout; "
                "battle symbols use ASCII."
            )
            return
        if arg in ("unicode", "utf8", "utf-8"):
            caller.db.ui_mode = "fancy"
            caller.db.battle_ascii_symbols = False
            caller.msg(
                "UI mode set to unicode. Room display uses fancy layout; "
                "battle symbols use Unicode."
            )
            return
        mode = mapping.get(arg)
        if not mode:
            caller.msg(
                "Usage: +uimode <fancy||simple||boxed||screenreader||ascii||unicode>"
            )
            return
        caller.db.ui_mode = mode
        pretty = "screenreader" if mode == "sr" else mode
        caller.msg(f"UI mode set to {pretty}.")

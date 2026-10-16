"""Resume a pending nickname choice after capturing a Pokémon."""

from evennia import Command

from menus.capture_nickname import start_capture_nickname


class CmdCaptureNickname(Command):
    """Resume a captured Pokémon's nickname prompt with +nickname."""

    key = "+nickname"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        """Start a pending capture choice when the player is free to answer."""
        if not start_capture_nickname(self.caller):
            self.caller.msg("No nickname prompt can be opened right now. Finish your battle or menu first, or capture a Pokémon.")

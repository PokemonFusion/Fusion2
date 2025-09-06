from __future__ import annotations

"""Development helper commands."""

from evennia import default_cmds
from evennia.utils import evmenu


class CmdTestRoomWizard(default_cmds.MuxCommand):
    """Launch the enhanced testing room wizard."""

    key = "@testrw"
    locks = "cmd:perm(Builders)"
    help_category = "Building"

    def func(self) -> None:  # type: ignore[override]
        """Run the room wizard EvMenu."""
        evmenu.EvMenu(
            self.caller,
            "fusion2.commands.wizards.room_wizard",
            startnode="node_start",
            auto_quit=True,
            persistent=False,
            cmd_on_exit=None,
            cmdset_mergetype="Union",
        )


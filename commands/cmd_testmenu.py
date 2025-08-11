"""Command to launch a simple test :class:`~evennia.utils.evmenu.EvMenu`.

This is mainly intended as a sanity-check for the menu system and is not
used in normal gameplay. The command exposes a persistent toggle so one can
compare the behavior of standard vs persistent menus.
"""

from evennia import Command
from evennia.utils.evmenu import EvMenu

# Import the module containing the menu node functions directly so Evennia does
# not have to resolve a module path string. Importing the module object avoids
# issues when the project's package name differs across environments.
from utils import evmenu_sanity

class CmdTestMenu(Command):
    """
    Launch a stock EvMenu sanity-check.

    Usage:
        testmenu
        testmenu persistent
    """

    key = "testmenu"
    locks = "cmd:all()"

    def func(self):
        persistent = "persistent" in self.args.lower()
        EvMenu(
            self.caller,
            evmenu_sanity,                   # module containing the menu nodes
            startnode="node_start",
            auto_quit=True,                  # default 'q' to quit
            persistent=persistent,           # try toggling this to compare behaviors
            cmd_on_exit="look",              # useful to see where you land after quit
        )

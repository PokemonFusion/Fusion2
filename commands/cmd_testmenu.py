# fusion2/commands/cmd_testmenu.py
from evennia import Command
from evennia.utils.evmenu import EvMenu

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
            "fusion2.utils.evmenu_sanity",   # module path to the nodes above
            startnode="node_start",
            auto_quit=True,                  # default 'q' to quit
            persistent=persistent,           # try toggling this to compare behaviors
            cmd_on_exit="look",              # useful to see where you land after quit
        )

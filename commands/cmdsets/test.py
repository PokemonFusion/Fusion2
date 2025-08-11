"""CmdSet used for development testing via EvMenu."""

from evennia import CmdSet
from commands.debug.cmd_testmenu import CmdTestMenu
from commands.debug.cmd_testmenu_enh import CmdTestMenuEnhanced


class TestCmdSet(CmdSet):
    """CmdSet containing temporary testing commands."""

    key = "TestCmdSet"
    priority = 2

    def at_cmdset_creation(self):
        """Populate the cmdset."""
        self.add(CmdTestMenu())
        self.add(CmdTestMenuEnhanced())

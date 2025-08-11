"""CmdSet for economy and map related commands."""

from evennia import CmdSet
from commands.cmd_store import CmdStore
from commands.cmd_pokestore import CmdPokestore
from commands.cmdmapmove import CmdMapMove
from commands.cmdstartmap import CmdStartMap


class EconomyMapCmdSet(CmdSet):
    """CmdSet combining economy and world map commands."""

    key = "EconomyMapCmdSet"

    def at_cmdset_creation(self):
        """Populate the cmdset."""
        for cmd in (CmdStore, CmdPokestore, CmdMapMove, CmdStartMap):
            self.add(cmd())

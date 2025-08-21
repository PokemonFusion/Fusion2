"""CmdSet for Pokédex lookup commands."""

from evennia import CmdSet
from commands.player.cmd_pokedex import (
    CmdPokedexSearch,
    CmdPokedexAll,
    CmdMovedexSearch,
    CmdMovesetSearch,
    CmdPokedexNumber,
    CmdStarterList,
)


class PokedexCmdSet(CmdSet):
    """CmdSet containing commands querying Pokédex data."""

    key = "PokedexCmdSet"

    def at_cmdset_creation(self):
        """Populate the cmdset."""
        for cmd in (
            CmdPokedexSearch,
            CmdPokedexAll,
            CmdMovedexSearch,
            CmdMovesetSearch,
            CmdPokedexNumber,
            CmdStarterList,
        ):
            self.add(cmd())

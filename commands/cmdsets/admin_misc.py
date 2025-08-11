"""CmdSet for miscellaneous administrative commands."""

from evennia import CmdSet
from commands.cmd_givepokemon import CmdGivePokemon
from commands.cmd_adminpokemon import CmdListPokemon, CmdRemovePokemon, CmdPokemonInfo
from commands.cmd_gitpull import CmdGitPull
from commands.cmd_logusage import CmdLogUsage, CmdMarkVerified


class AdminMiscCmdSet(CmdSet):
    """CmdSet bundling various admin tools."""

    key = "AdminMiscCmdSet"

    def at_cmdset_creation(self):
        """Populate the cmdset."""
        for cmd in (
            CmdGivePokemon,
            CmdListPokemon,
            CmdRemovePokemon,
            CmdPokemonInfo,
            CmdGitPull,
            CmdLogUsage,
            CmdMarkVerified,
        ):
            self.add(cmd())

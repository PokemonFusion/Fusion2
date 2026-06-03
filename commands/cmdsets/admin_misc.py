"""CmdSet for miscellaneous administrative commands."""

from evennia import CmdSet

from commands.admin.cmd_adminpokemon import (
	CmdBackfillPokemonMovesets,
	CmdListPokemon,
	CmdPokemonInfo,
	CmdRemovePokemon,
)
from commands.admin.cmd_fixfusion import CmdFixFusion
from commands.admin.cmd_fusionboost import CmdFusionBoost
from commands.admin.cmd_gitpull import CmdGitPull
from commands.admin.cmd_givepokemon import CmdGivePokemon
from commands.admin.cmd_heartbeat import CmdHeartbeat
from commands.admin.cmd_landingnote import CmdLandingNote
from commands.admin.cmd_sitestatus import CmdSiteStatus
from commands.debug.cmd_logusage import CmdLogUsage, CmdMarkVerified


class AdminMiscCmdSet(CmdSet):
	"""CmdSet bundling various admin tools."""

	key = "AdminMiscCmdSet"

	def at_cmdset_creation(self):
		"""Populate the cmdset."""
		for cmd in (
			CmdGivePokemon,
			CmdListPokemon,
			CmdRemovePokemon,
			CmdBackfillPokemonMovesets,
                        CmdPokemonInfo,
                        CmdFixFusion,
                        CmdFusionBoost,
                        CmdGitPull,
                        CmdHeartbeat,
                        CmdLandingNote,
                        CmdSiteStatus,
                        CmdLogUsage,
                        CmdMarkVerified,
                ):
			self.add(cmd())

"""CmdSet for world building and administration commands."""

from evennia import CmdSet

from commands.admin.cmd_alphaspawnapply import CmdAlphaSpawnApply
from commands.admin.cmd_alphaspawndiff import CmdAlphaSpawnDiff
from commands.admin.cmd_editroom import CmdEditRoom
from commands.admin.cmd_roomwizard import CmdRoomWizard
from commands.admin.cmd_spawncompare import CmdSpawnCompare
from commands.admin.cmd_spawnhunttest import CmdSpawnHuntTest
from commands.admin.cmd_spawnmigratepreview import CmdSpawnMigratePreview
from commands.admin.cmd_spawnprofilecompare import CmdSpawnProfileCompare
from commands.admin.cmd_spawnprofilehunttest import CmdSpawnProfileHuntTest
from commands.admin.cmd_spawnprofilepreview import CmdSpawnProfilePreview
from commands.admin.cmd_spawnprofilerolltest import CmdSpawnProfileRollTest
from commands.admin.cmd_spawnpreview import CmdSpawnPreview
from commands.admin.cmd_spawnrolltest import CmdSpawnRollTest
from commands.admin.cmd_spawns import CmdSpawns
from commands.admin.cmd_spawnspecialprobe import CmdSpawnSpecialProbe
from commands.admin.cmd_validate import CmdValidate
from commands.player.cmd_chargen import CmdChargen


class WorldBuildCmdSet(CmdSet):
	"""CmdSet containing commands used for building the world."""

	key = "WorldBuildCmdSet"

	def at_cmdset_creation(self):
		"""Populate the cmdset."""
		for cmd in (
			CmdChargen,
			CmdRoomWizard,
			CmdEditRoom,
			CmdValidate,
			CmdSpawns,
			CmdAlphaSpawnDiff,
			CmdAlphaSpawnApply,
			CmdSpawnMigratePreview,
			CmdSpawnPreview,
			CmdSpawnRollTest,
			CmdSpawnCompare,
			CmdSpawnHuntTest,
			CmdSpawnProfilePreview,
			CmdSpawnProfileRollTest,
			CmdSpawnProfileCompare,
			CmdSpawnProfileHuntTest,
			CmdSpawnSpecialProbe,
		):
			self.add(cmd())

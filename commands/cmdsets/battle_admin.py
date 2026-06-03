"""CmdSet for administrative battle commands."""

from evennia import CmdSet

from commands.admin.cmd_adminbattle import (
    CmdAbortBattle,
    CmdBattleCleanup,
    CmdBattleInfo,
    CmdBattleSnapshot,
    CmdRestoreBattle,
    CmdRetryTurn,
    CmdToggleDamageNumbers,
    CmdUiPreview,
)
from commands.admin.cmd_aidebug import CmdAIDebugTrace
from commands.admin.cmd_gymbattle import CmdGymBattle
from commands.admin.cmd_npcbattle import CmdNPCBattle
from commands.admin.cmd_testbattle import CmdStartTestBattle, CmdTestSpawn


class BattleAdminCmdSet(CmdSet):
    """CmdSet with admin-only battle helpers."""

    key = "BattleAdminCmdSet"

    def at_cmdset_creation(self):
        """Populate the cmdset."""
        for cmd in (
            CmdAbortBattle,
            CmdBattleCleanup,
            CmdRestoreBattle,
            CmdBattleInfo,
            CmdBattleSnapshot,
            CmdAIDebugTrace,
            CmdRetryTurn,
            CmdToggleDamageNumbers,
            CmdUiPreview,
            CmdNPCBattle,
            CmdGymBattle,
            CmdTestSpawn,
            CmdStartTestBattle,
        ):
            self.add(cmd())

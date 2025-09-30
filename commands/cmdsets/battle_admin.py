"""CmdSet for administrative battle commands."""

from evennia import CmdSet

from commands.admin.cmd_adminbattle import (
    CmdAbortBattle,
    CmdBattleInfo,
    CmdBattleSnapshot,
    CmdRestoreBattle,
    CmdRetryTurn,
    CmdToggleDamageNumbers,
    CmdUiPreview,
)


class BattleAdminCmdSet(CmdSet):
    """CmdSet with admin-only battle helpers."""

    key = "BattleAdminCmdSet"

    def at_cmdset_creation(self):
        """Populate the cmdset."""
        for cmd in (
            CmdAbortBattle,
            CmdRestoreBattle,
            CmdBattleInfo,
            CmdBattleSnapshot,
            CmdRetryTurn,
            CmdToggleDamageNumbers,
            CmdUiPreview,
        ):
            self.add(cmd())

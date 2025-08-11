"""CmdSet for administrative battle commands."""

from evennia import CmdSet
from commands.cmd_adminbattle import (
    CmdAbortBattle,
    CmdRestoreBattle,
    CmdBattleInfo,
    CmdRetryTurn,
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
            CmdRetryTurn,
            CmdUiPreview,
        ):
            self.add(cmd())

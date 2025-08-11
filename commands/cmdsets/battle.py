"""CmdSet for battle related commands."""

from evennia import CmdSet
from commands.cmd_battle import CmdBattleAttack, CmdBattleSwitch, CmdBattleItem, CmdBattleFlee
from commands.cmd_watchbattle import CmdWatchBattle, CmdUnwatchBattle
from commands.cmd_watch import CmdWatch, CmdUnwatch
from commands.cmd_debugbattle import CmdDebugBattle


class BattleCmdSet(CmdSet):
    """CmdSet grouping commands used during battles."""

    key = "BattleCmdSet"

    def at_cmdset_creation(self):
        """Populate the cmdset."""
        for cmd in (
            CmdBattleAttack,
            CmdBattleSwitch,
            CmdBattleItem,
            CmdBattleFlee,
            CmdWatchBattle,
            CmdUnwatchBattle,
            CmdWatch,
            CmdUnwatch,
            CmdDebugBattle,
        ):
            self.add(cmd())

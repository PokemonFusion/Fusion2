"""CmdSet for battle related commands."""

from evennia import CmdSet

from commands.debug.cmd_debugbattle import CmdDebugBattle
from commands.debug.cmd_movedata import CmdDebugMoveData
from commands.player.cmd_battle_attack import CmdBattleAttack
from commands.player.cmd_battle_flee import CmdBattleFlee
from commands.player.cmd_battle_item import CmdBattleItem
from commands.player.cmd_battle_switch import CmdBattleSwitch
from commands.player.cmd_showbattle import CmdShowBattle
from commands.player.cmd_watch import CmdUnwatch, CmdWatch
from commands.player.cmd_watchbattle import CmdUnwatchBattle, CmdWatchBattle


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
            CmdShowBattle,
            CmdWatch,
            CmdUnwatch,
            CmdDebugBattle,
            CmdDebugMoveData,
        ):
            self.add(cmd())

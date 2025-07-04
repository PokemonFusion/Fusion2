from evennia import CmdSet
from .cmdmapmove import CmdMapMove
from .cmdstartmap import CmdStartMap


class MapCmdSet(CmdSet):
    key = "MapCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdMapMove())
        self.add(CmdStartMap())

"""Command set exposing development-only status helpers."""

from evennia import CmdSet

from commands.dev.cmd_statusdev import CmdStatusDev


class TestCmdSet(CmdSet):
        """Temporary command set exposing status testing helpers."""

        key = "TestCmdSet"

        def at_cmdset_creation(self):
                self.add(CmdStatusDev())

"""Command to toggle the temporary testing CmdSet."""

try:  # pragma: no cover - Allow import without full Evennia settings
    from evennia import Command  # type: ignore
except Exception:  # pragma: no cover - fallback when Evennia is missing
    Command = None  # type: ignore

if Command is None:  # pragma: no cover - define stub when Evennia not loaded
    class Command:  # type: ignore[misc]
        """Fallback Command stub used during test collection."""

        pass


class CmdToggleTest(Command):
    """Toggle the developer test cmdset on the caller."""

    key = "toggletest"
    locks = "cmd:perm(Builders)"

    def func(self):
        from commands.cmdsets.test import TestCmdSet

        if self.caller.cmdset.has_cmdset(TestCmdSet, must_be_default=False):
            self.caller.cmdset.delete(TestCmdSet)
            self.caller.msg("|gTest cmdset removed.|n")
        else:
            self.caller.cmdset.add(TestCmdSet, persistent=False)
            self.caller.msg("|gTest cmdset added.|n")

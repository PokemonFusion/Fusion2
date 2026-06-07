"""Temporary command sets used while inside an Adventure."""

from __future__ import annotations

try:
    from evennia import CmdSet, Command
except Exception:  # pragma: no cover - lightweight test fallback
    CmdSet = None  # type: ignore[assignment]
    Command = None  # type: ignore[assignment]

if Command is None:  # pragma: no cover - lightweight test fallback
    class Command:  # type: ignore[no-redef]
        pass

if CmdSet is None:  # pragma: no cover - lightweight test fallback
    class CmdSet:  # type: ignore[no-redef]
        def add(self, *_args, **_kwargs):
            return None

from .constants import ADVENTURE_CMDSET_KEY


class AdventureMoveCommand(Command):
    """Move within the active virtual Adventure map."""

    key = "north"
    aliases = ["n"]
    locks = "cmd:all()"
    help_category = "Adventure"
    direction = "north"
    arg_regex = r"$"

    def func(self):
        from .renderer import render_session
        from .sessions import move_session

        result = move_session(self.caller, self.direction)
        self.caller.msg(result.message)
        if result.ok and result.session is not None:
            self.caller.msg(render_session(result.session))


class CmdAdventureNorth(AdventureMoveCommand):
    key = "north"
    aliases = ["n"]
    direction = "north"


class CmdAdventureSouth(AdventureMoveCommand):
    key = "south"
    aliases = ["s"]
    direction = "south"


class CmdAdventureEast(AdventureMoveCommand):
    key = "east"
    aliases = ["e"]
    direction = "east"


class CmdAdventureWest(AdventureMoveCommand):
    key = "west"
    aliases = ["w"]
    direction = "west"


class AdventureMovementCmdSet(CmdSet):
    """Cardinal movement commands mounted only during an Adventure."""

    key = ADVENTURE_CMDSET_KEY

    def at_cmdset_creation(self):
        self.add(CmdAdventureNorth())
        self.add(CmdAdventureSouth())
        self.add(CmdAdventureEast())
        self.add(CmdAdventureWest())


def attach_movement_cmdset(player) -> None:
    """Attach Adventure cardinal commands to ``player`` if possible."""

    cmdset = getattr(player, "cmdset", None)
    if cmdset is None:
        return
    has_cmdset = getattr(cmdset, "has_cmdset", None)
    if callable(has_cmdset):
        try:
            if has_cmdset(AdventureMovementCmdSet, must_be_default=False):
                return
        except TypeError:
            if has_cmdset(ADVENTURE_CMDSET_KEY):
                return
    add = getattr(cmdset, "add", None)
    if callable(add):
        try:
            add(AdventureMovementCmdSet, persistent=False)
        except TypeError:
            add(AdventureMovementCmdSet())


def detach_movement_cmdset(player) -> None:
    """Remove Adventure cardinal commands from ``player`` if possible."""

    cmdset = getattr(player, "cmdset", None)
    delete = getattr(cmdset, "delete", None) if cmdset is not None else None
    if callable(delete):
        try:
            delete(AdventureMovementCmdSet)
        except TypeError:
            delete(ADVENTURE_CMDSET_KEY)

"""Commands to manage watching ongoing battles."""

from __future__ import annotations

from evennia import Command

from utils.locks import require_no_battle_lock
from world.system_init import get_system


class CmdWatchBattle(Command):
    """Start watching a battle.

    Usage:
      +watch/battle <battle id>

    Examples:
      +watch/battle 12

    Notes:
      Use +battles to list active battle ids.
    """

    key = "+watch/battle"
    aliases = ["+battlewatch"]
    locks = "cmd:all()"
    help_category = "Pokemon/Battle"

    def func(self):
        if not require_no_battle_lock(self.caller):
            return
        if not self.args or not self.args.strip().isdigit():
            self.caller.msg("Usage: +watch/battle <battle id>")
            return
        bid = int(self.args.strip())
        system = get_system()
        manager = getattr(system, "battle_manager", None)
        if not manager or not manager.watch(bid, self.caller):
            self.caller.msg("No battle with that ID found.")
            return
        self.caller.msg(f"You begin watching battle #{bid}.")


class CmdUnwatchBattle(Command):
    """Stop watching a battle.

    Usage:
      +watch/stop <battle id>

    Examples:
      +watch/stop 12

    Notes:
      This is for battle-id watching. Use +unwatch to stop watching your
      current observed battle session.
    """

    key = "+watch/stop"
    aliases = ["+battleunwatch"]
    locks = "cmd:all()"
    help_category = "Pokemon/Battle"

    def func(self):
        if not require_no_battle_lock(self.caller):
            return
        if not self.args or not self.args.strip().isdigit():
            self.caller.msg("Usage: +watch/stop <battle id>")
            return
        bid = int(self.args.strip())
        system = get_system()
        manager = getattr(system, "battle_manager", None)
        if not manager or not manager.unwatch(bid, self.caller):
            self.caller.msg("No battle with that ID found.")
            return
        self.caller.msg(f"You stop watching battle #{bid}.")


class CmdBattleMute(Command):
    """Mute updates from a battle.

    Usage:
      +watch/mute <battle id>

    Examples:
      +watch/mute 12

    Notes:
      Muting stops updates for that watched battle id.
    """

    key = "+watch/mute"
    aliases = ["+battlemute"]
    locks = "cmd:all()"
    help_category = "Pokemon/Battle"

    def func(self):
        if not require_no_battle_lock(self.caller):
            return
        if not self.args or not self.args.strip().isdigit():
            self.caller.msg("Usage: +watch/mute <battle id>")
            return
        bid = int(self.args.strip())
        system = get_system()
        manager = getattr(system, "battle_manager", None)
        if not manager or not manager.unwatch(bid, self.caller):
            self.caller.msg("No battle with that ID found.")
            return
        self.caller.msg(f"You mute battle #{bid}.")


class CmdBattleList(Command):
    """List all active battles.

    Usage:
      +battles

    Examples:
      +battles

    Notes:
      Use +watch/battle <id> to spectate one of the listed battles.
    """

    key = "+battles"
    aliases = ["+battlelist"]
    locks = "cmd:all()"
    help_category = "Pokemon/Battle"

    def func(self):
        system = get_system()
        manager = getattr(system, "battle_manager", None)
        if not manager:
            self.caller.msg("Battle manager unavailable.")
            return
        insts = getattr(manager.ndb, "instances", {})
        if not insts:
            self.caller.msg("No active battles.")
            return
        lines = ["|wActive battles|n"]
        for bid in sorted(insts):
            lines.append(f"  {bid}")
        self.caller.msg("\n".join(lines))

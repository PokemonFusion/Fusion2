"""Commands to manage watching ongoing battles."""

from __future__ import annotations

from evennia import Command

from utils.locks import require_no_battle_lock
from world.system_init import get_system


class CmdBattleWatch(Command):
        """Start watching a battle.

        Usage:
          +battlewatch <battle id>
        """

        key = "+battlewatch"
        locks = "cmd:all()"
        help_category = "Pokemon"

        def func(self):
                if not require_no_battle_lock(self.caller):
                        return
                if not self.args or not self.args.strip().isdigit():
                        self.caller.msg("Usage: +battlewatch <battle id>")
                        return
                bid = int(self.args.strip())
                system = get_system()
                manager = getattr(system, "battle_manager", None)
                if not manager or not manager.watch(bid, self.caller):
                        self.caller.msg("No battle with that ID found.")
                        return
                self.caller.msg(f"You begin watching battle #{bid}.")


class CmdBattleUnwatch(Command):
        """Stop watching a battle.

        Usage:
          +battleunwatch <battle id>
        """

        key = "+battleunwatch"
        locks = "cmd:all()"
        help_category = "Pokemon"

        def func(self):
                if not require_no_battle_lock(self.caller):
                        return
                if not self.args or not self.args.strip().isdigit():
                        self.caller.msg("Usage: +battleunwatch <battle id>")
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
          +battlemute <battle id>
        """

        key = "+battlemute"
        locks = "cmd:all()"
        help_category = "Pokemon"

        def func(self):
                if not require_no_battle_lock(self.caller):
                        return
                if not self.args or not self.args.strip().isdigit():
                        self.caller.msg("Usage: +battlemute <battle id>")
                        return
                bid = int(self.args.strip())
                system = get_system()
                manager = getattr(system, "battle_manager", None)
                if not manager or not manager.unwatch(bid, self.caller):
                        self.caller.msg("No battle with that ID found.")
                        return
                self.caller.msg(f"You mute battle #{bid}.")


class CmdBattleList(Command):
        """List all active battles."""

        key = "+battlelist"
        locks = "cmd:all()"
        help_category = "Pokemon"

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

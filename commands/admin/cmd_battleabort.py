"""Administrative command to abort battles with standard rules."""

from __future__ import annotations

from evennia import Command, search_object

from utils.locks import require_no_battle_lock
from world.system_init import get_system


class CmdBattleAbort(Command):
        """Abort a battle, invalidating or forfeiting as appropriate.

        Usage:
          +battleabort <battle id> <player>
        """

        key = "+battleabort"
        locks = "cmd:perm(Wizards)"
        help_category = "Admin"

        def func(self):
                if not require_no_battle_lock(self.caller):
                        return
                if not self.args:
                        self.caller.msg("Usage: +battleabort <battle id> <player>")
                        return
                parts = self.args.split(maxsplit=1)
                if len(parts) != 2 or not parts[0].isdigit():
                        self.caller.msg("Usage: +battleabort <battle id> <player>")
                        return
                bid = int(parts[0])
                target_list = search_object(parts[1])
                if not target_list:
                        self.caller.msg("No such character.")
                        return
                target = target_list[0]
                system = get_system()
                manager = getattr(system, "battle_manager", None)
                if not manager or not manager.abort_request(bid, target):
                        self.caller.msg("No battle with that ID found.")
                        return
                self.caller.msg(f"Battle #{bid} aborted.")

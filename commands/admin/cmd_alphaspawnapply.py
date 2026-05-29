"""Admin command for guarded Alpha spawn seed/live syncing."""

from __future__ import annotations

from evennia import Command

from commands.admin.cmd_alphaspawndiff import lookup_live_alpha_room
from pokemon.spawns.alpha_sync import (
    AlphaSpawnSyncError,
    apply_alpha_spawn_seed_updates,
    format_alpha_spawn_apply,
)


class CmdAlphaSpawnApply(Command):
    """Apply cleaned Alpha seed hunt_chart data to existing live Alpha rooms.

    Usage:
      @alphaspawnapply

    This command refuses to write if any Alpha room is not marked safe by the
    Alpha spawn diff helper.
    """

    key = "@alphaspawnapply"
    aliases = ["+alphaspawnapply", "+alpha/spawnapply"]
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        try:
            result = apply_alpha_spawn_seed_updates(live_room_lookup=lookup_live_alpha_room)
        except AlphaSpawnSyncError as err:
            self.caller.msg(f"Alpha spawn apply error: {err}")
            return
        self.caller.msg(format_alpha_spawn_apply(result))


__all__ = ["CmdAlphaSpawnApply"]

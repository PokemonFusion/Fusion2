"""Admin command for read-only Alpha spawn seed/live diffing."""

from __future__ import annotations

from evennia import Command

from pokemon.spawns.alpha_sync import (
    AlphaLiveRoomMatch,
    AlphaSpawnSyncError,
    compare_alpha_spawn_data,
    format_alpha_spawn_diff,
)


class CmdAlphaSpawnDiff(Command):
    """Compare live Alpha room hunt_chart attrs to the cleaned seed file.

    Usage:
      @alphaspawndiff
    """

    key = "@alphaspawndiff"
    aliases = ["+alphaspawndiff", "+alpha/spawndiff"]
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        try:
            report = compare_alpha_spawn_data(live_room_lookup=lookup_live_alpha_room)
        except AlphaSpawnSyncError as err:
            self.caller.msg(f"Alpha spawn diff error: {err}")
            return
        self.caller.msg(format_alpha_spawn_diff(report))


def lookup_live_alpha_room(room_key: str) -> AlphaLiveRoomMatch:
    from evennia.objects.models import ObjectDB

    matches = list(ObjectDB.objects.filter(db_key=room_key).order_by("id"))
    if not matches:
        return AlphaLiveRoomMatch(room=None)
    if len(matches) > 1:
        dbrefs = ", ".join(f"#{match.id}" for match in matches)
        return AlphaLiveRoomMatch(
            room=None,
            error=f"Multiple live rooms found for {room_key!r}: {dbrefs}.",
        )
    return AlphaLiveRoomMatch(room=matches[0])


__all__ = ["CmdAlphaSpawnDiff", "lookup_live_alpha_room"]

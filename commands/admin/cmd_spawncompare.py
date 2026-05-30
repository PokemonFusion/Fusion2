"""Admin command for comparing live hunt data to PF2 spawn adapters."""

from __future__ import annotations

from evennia import Command

from pokemon.spawns.adapters import SpawnAdapterError
from pokemon.spawns.compare import (
    SpawnCompareError,
    compare_room_spawns,
    format_spawn_comparison,
)
from pokemon.spawns.preview import parse_preview_band


class CmdSpawnCompare(Command):
    """Compare live room hunt interpretation to the PF2 spawn adapter.

    Usage:
      @spawncompare
      @spawncompare <band>
    """

    key = "@spawncompare"
    aliases = ["+spawncompare", "+spawn/compare"]
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        room = getattr(caller, "location", None)
        if not room:
            caller.msg("You must be in a room to compare spawn data.")
            return

        try:
            band = parse_preview_band(self.args)
        except ValueError as err:
            caller.msg(str(err))
            return

        try:
            comparison = compare_room_spawns(room, band=band)
        except SpawnAdapterError as err:
            caller.msg(f"Spawn compare adapter error: {err}")
            return
        except SpawnCompareError as err:
            caller.msg(f"Spawn compare live-data error: {err}")
            return

        caller.msg(format_spawn_comparison(comparison))


__all__ = ["CmdSpawnCompare"]

"""Admin command for previewing PF2 spawn adapter output."""

from __future__ import annotations

from evennia import Command

from pokemon.spawns.adapters import SpawnAdapterError, spawn_chart_from_room
from pokemon.spawns.preview import format_spawn_preview, parse_preview_band


def detect_room_spawn_source(room) -> str:
    db = getattr(room, "db", None)
    if getattr(db, "hunt_chart", None):
        return "hunt_chart"
    if getattr(db, "spawn_table", None):
        return "spawn_table"
    return "empty"


class CmdSpawnPreview(Command):
    """Preview how PF2 spawn adapters interpret this room.

    Usage:
      @spawnpreview
      @spawnpreview <band>
    """

    key = "@spawnpreview"
    aliases = ["+spawnpreview", "+spawn/preview"]
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        room = getattr(caller, "location", None)
        if not room:
            caller.msg("You must be in a room to preview spawn data.")
            return

        try:
            band = parse_preview_band(self.args)
        except ValueError as err:
            caller.msg(str(err))
            return

        try:
            chart = spawn_chart_from_room(room)
        except SpawnAdapterError as err:
            caller.msg(f"Spawn preview error: {err}")
            return

        source = detect_room_spawn_source(room)
        caller.msg(format_spawn_preview(chart, source=source, band=band))


__all__ = ["CmdSpawnPreview", "detect_room_spawn_source"]

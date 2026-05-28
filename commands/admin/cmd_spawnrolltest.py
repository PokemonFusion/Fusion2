"""Admin command for dry-running PF2 spawn rolls."""

from __future__ import annotations

from evennia import Command

from commands.admin.cmd_spawnpreview import detect_room_spawn_source
from pokemon.spawns.adapters import SpawnAdapterError, spawn_chart_from_room
from pokemon.spawns.rolltest import (
    format_spawn_roll_test,
    parse_rolltest_args,
    run_spawn_roll_test,
)


class CmdSpawnRollTest(Command):
    """Dry-run PF2 spawn rolls for this room without starting battles.

    Usage:
      @spawnrolltest
      @spawnrolltest <band>
      @spawnrolltest <band> <count>
    """

    key = "@spawnrolltest"
    aliases = ["+spawnrolltest", "+spawn/rolltest"]
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        room = getattr(caller, "location", None)
        if not room:
            caller.msg("You must be in a room to test spawn rolls.")
            return

        try:
            options = parse_rolltest_args(self.args)
        except ValueError as err:
            caller.msg(str(err))
            return

        try:
            chart = spawn_chart_from_room(room)
        except SpawnAdapterError as err:
            caller.msg(f"Spawn roll test error: {err}")
            return

        result = run_spawn_roll_test(
            chart,
            band=options.band,
            count=options.count,
            requested_count=options.requested_count,
        )
        source = detect_room_spawn_source(room)
        caller.msg(format_spawn_roll_test(result, source=source))


__all__ = ["CmdSpawnRollTest"]

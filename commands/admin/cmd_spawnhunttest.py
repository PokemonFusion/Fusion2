"""Admin command for starting an adapter-backed PF2 wild battle test."""

from __future__ import annotations

from evennia import Command

from pokemon.spawns.adapters import SpawnAdapterError, spawn_chart_from_room
from pokemon.spawns.hunttest import (
    SpawnHuntTestError,
    parse_hunttest_band,
    run_spawn_hunt_test,
)
from utils.dex_suggestions import is_species_not_found_error, species_not_found_message


class CmdSpawnHuntTest(Command):
    """Start one wild debug battle using the PF2 spawn adapter/core path.

    Usage:
      @spawnhunttest
      @spawnhunttest <band>
    """

    key = "@spawnhunttest"
    aliases = ["+spawnhunttest", "+spawn/hunttest"]
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        room = getattr(caller, "location", None)
        if not room:
            caller.msg("You must be in a room to test spawn hunting.")
            return

        try:
            band = parse_hunttest_band(self.args)
        except ValueError as err:
            caller.msg(str(err))
            return

        try:
            chart = spawn_chart_from_room(room)
            result = run_spawn_hunt_test(caller, chart, band=band)
        except SpawnAdapterError as err:
            caller.msg(f"Spawn hunt test adapter error: {err}")
            return
        except SpawnHuntTestError as err:
            caller.msg(str(err))
            return
        except ValueError as err:
            roll = getattr(locals().get("result", None), "roll", None)
            species = getattr(roll, "species_id", "")
            if species and is_species_not_found_error(err):
                caller.msg(species_not_found_message(species))
                return
            caller.msg(f"Spawn hunt test error: {err}")
            return

        roll = result.roll
        caller.msg(
            "PF2 spawn hunt test started battle "
            f"#{result.battle_id}: {roll.species_id} Lv{roll.level} "
            f"({roll.frequency}, band {roll.band})."
        )


__all__ = ["CmdSpawnHuntTest"]

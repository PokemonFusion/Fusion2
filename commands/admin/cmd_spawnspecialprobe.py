"""Admin command for read-only PF2 special spawn probing."""

from __future__ import annotations

from evennia import Command

from pokemon.spawns.adapters import SpawnAdapterError, spawn_chart_from_room
from pokemon.spawns.profile_data import SpawnProfileDataError
from pokemon.spawns.profiles import SpawnProfileError
from pokemon.spawns.special_probe import (
    SPECIAL_PROBE_PROFILE_SOURCE,
    SPECIAL_PROBE_ROOM_SOURCE,
    format_special_spawn_probe,
    parse_special_probe_args,
    run_profile_special_spawn_probe,
    run_special_spawn_probe,
)


class CmdSpawnSpecialProbe(Command):
    """Probe special spawn eligibility without changing hunt or battle state.

    Usage:
      @spawnspecialprobe room [current_tick] [last_special_tick] [seconds_since_last_special]
      @spawnspecialprobe profile <area_key> [current_tick] [last_special_tick] [seconds_since_last_special]
    """

    key = "@spawnspecialprobe"
    aliases = ["+spawnspecialprobe", "+spawn/specialprobe"]
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        try:
            options = parse_special_probe_args(self.args)
        except ValueError as err:
            caller.msg(str(err))
            return

        if options.source == SPECIAL_PROBE_ROOM_SOURCE:
            room = getattr(caller, "location", None)
            if not room:
                caller.msg("You must be in a room to probe room-backed special spawns.")
                return
            try:
                chart = spawn_chart_from_room(room)
            except SpawnAdapterError as err:
                caller.msg(f"Special spawn probe error: {err}")
                return
            result = run_special_spawn_probe(
                chart,
                source=SPECIAL_PROBE_ROOM_SOURCE,
                state=options.state,
            )
            caller.msg(format_special_spawn_probe(result))
            return

        if options.source == SPECIAL_PROBE_PROFILE_SOURCE:
            try:
                result = run_profile_special_spawn_probe(
                    options.area_key,
                    state=options.state,
                )
            except (SpawnProfileDataError, SpawnProfileError) as err:
                caller.msg(f"Special spawn probe error: {err}")
                return
            caller.msg(format_special_spawn_probe(result))
            return

        caller.msg("Unknown special spawn probe source.")


__all__ = ["CmdSpawnSpecialProbe"]

"""Admin command for starting a profile-backed PF2 wild battle test."""

from __future__ import annotations

from evennia import Command

from pokemon.spawns.hunttest import SpawnHuntTestError
from pokemon.spawns.profile_data import SpawnProfileDataError
from pokemon.spawns.profile_hunttest import parse_profile_hunttest_args, run_profile_spawn_hunt_test
from pokemon.spawns.profiles import SpawnProfileError


class CmdSpawnProfileHuntTest(Command):
    """Start one wild debug battle using sample PF2 profile data.

    Usage:
      @spawnprofilehunttest <area_key>
      @spawnprofilehunttest <area_key> <band>
    """

    key = "@spawnprofilehunttest"
    aliases = ["+spawnprofilehunttest", "+spawn/profilehunttest"]
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        if not getattr(caller, "location", None):
            caller.msg("You must be in a room to test profile spawn hunting.")
            return

        try:
            options = parse_profile_hunttest_args(self.args)
            result = run_profile_spawn_hunt_test(caller, options.area_key, band=options.band)
        except (SpawnProfileDataError, SpawnProfileError) as err:
            caller.msg(f"Spawn profile hunt test error: {err}")
            return
        except SpawnHuntTestError as err:
            caller.msg(str(err))
            return
        except ValueError as err:
            caller.msg(f"Spawn profile hunt test error: {err}")
            return

        roll = result.roll
        caller.msg(
            "PF2 profile spawn hunt test started battle "
            f"#{result.battle_id}: area {options.area_key}, "
            f"{roll.species_id} Lv{roll.level} ({roll.frequency}, band {roll.band})."
        )


__all__ = ["CmdSpawnProfileHuntTest"]

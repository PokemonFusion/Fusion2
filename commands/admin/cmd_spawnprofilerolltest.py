"""Admin command for roll-testing sample file-backed PF2 spawn profiles."""

from __future__ import annotations

from evennia import Command

from pokemon.spawns.profile_data import SpawnProfileDataError
from pokemon.spawns.profile_rolltest import (
    PROFILE_ROLL_TEST_SOURCE,
    parse_profile_rolltest_args,
    run_profile_spawn_roll_test,
)
from pokemon.spawns.profiles import SpawnProfileError
from pokemon.spawns.rolltest import format_spawn_roll_test


class CmdSpawnProfileRollTest(Command):
    """Dry-run normal spawn rolls for a sample file-backed area profile.

    Usage:
      @spawnprofilerolltest <area_key> [band] [count]
    """

    key = "@spawnprofilerolltest"
    aliases = ["+spawnprofilerolltest", "+spawn/profilerolltest"]
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        try:
            options = parse_profile_rolltest_args(self.args)
            result = run_profile_spawn_roll_test(
                options.area_key,
                band=options.band,
                count=options.count,
                requested_count=options.requested_count,
            )
        except (SpawnProfileDataError, SpawnProfileError) as err:
            self.caller.msg(f"Spawn profile roll test error: {err}")
            return
        except ValueError as err:
            self.caller.msg(str(err))
            return

        self.caller.msg(format_spawn_roll_test(result, source=PROFILE_ROLL_TEST_SOURCE))


__all__ = ["CmdSpawnProfileRollTest"]

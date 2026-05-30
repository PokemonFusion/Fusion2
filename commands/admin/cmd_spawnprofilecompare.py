"""Admin command for auditing sample file-backed PF2 area profile resolution."""

from __future__ import annotations

from evennia import Command

from pokemon.spawns.profile_compare import compare_sample_profile_area, format_profile_spawn_comparison
from pokemon.spawns.profile_data import SpawnProfileDataError
from pokemon.spawns.profiles import SpawnProfileError


class CmdSpawnProfileCompare(Command):
    """Compare area profile entries to resolved sample SpawnChart output.

    Usage:
      @spawnprofilecompare <area_key>
    """

    key = "@spawnprofilecompare"
    aliases = ["+spawnprofilecompare", "+spawn/profilecompare"]
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        area_key = (self.args or "").strip()
        if not area_key:
            self.caller.msg("Usage: @spawnprofilecompare <area_key>")
            return
        try:
            comparison = compare_sample_profile_area(area_key)
        except (SpawnProfileDataError, SpawnProfileError) as err:
            self.caller.msg(f"Spawn profile compare error: {err}")
            return
        self.caller.msg(format_profile_spawn_comparison(comparison))


__all__ = ["CmdSpawnProfileCompare"]

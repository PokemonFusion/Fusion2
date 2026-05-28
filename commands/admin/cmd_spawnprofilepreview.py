"""Admin command for previewing sample file-backed PF2 spawn profiles."""

from __future__ import annotations

from evennia import Command

from pokemon.spawns.preview import format_spawn_preview
from pokemon.spawns.profile_data import SpawnProfileDataError, resolve_sample_area
from pokemon.spawns.profiles import SpawnProfileError


class CmdSpawnProfilePreview(Command):
    """Preview a sample file-backed PF2 area profile.

    Usage:
      @spawnprofilepreview <area_key>
    """

    key = "@spawnprofilepreview"
    aliases = ["+spawnprofilepreview", "+spawn/profilepreview"]
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        area_key = (self.args or "").strip()
        if not area_key:
            self.caller.msg("Usage: @spawnprofilepreview <area_key>")
            return
        try:
            chart = resolve_sample_area(area_key)
        except (SpawnProfileDataError, SpawnProfileError) as err:
            self.caller.msg(f"Spawn profile preview error: {err}")
            return
        self.caller.msg(format_spawn_preview(chart, source="sample file-backed profile data"))


__all__ = ["CmdSpawnProfilePreview"]

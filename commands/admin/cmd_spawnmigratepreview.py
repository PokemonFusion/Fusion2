"""Admin command for read-only legacy hunt_chart migration auditing."""

from __future__ import annotations

from evennia import Command

from pokemon.spawns.legacy_migration import audit_legacy_hunt_chart, format_legacy_hunt_chart_audit


class CmdSpawnMigratePreview(Command):
    """Preview PF2 recommendations for legacy room hunt_chart data.

    Usage:
      @spawnmigratepreview
    """

    key = "@spawnmigratepreview"
    aliases = ["+spawnmigratepreview", "+spawn/migratepreview"]
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        room = getattr(caller, "location", None)
        if not room:
            caller.msg("You must be in a room to preview legacy spawn migration.")
            return

        db = getattr(room, "db", None)
        area_key = (
            getattr(db, "spawn_area_key", None)
            or getattr(room, "key", None)
            or getattr(room, "id", None)
            or "unknown"
        )
        audit = audit_legacy_hunt_chart(getattr(db, "hunt_chart", None), area_key=area_key)
        caller.msg(format_legacy_hunt_chart_audit(audit))


__all__ = ["CmdSpawnMigratePreview"]

"""Wizard command for inspecting and controlling the global heartbeat."""

from __future__ import annotations

from evennia import Command

from world.heartbeat import (
    ensure_heartbeat_script,
    format_heartbeat_jobs,
    format_heartbeat_status,
    get_heartbeat_script,
    run_heartbeat_tick,
    set_heartbeat_paused,
)


class CmdHeartbeat(Command):
    """Inspect or control the global heartbeat.

    Usage:
      @heartbeat
      @heartbeat/status
      @heartbeat/jobs
      @heartbeat/force
      @heartbeat/pause
      @heartbeat/resume
    """

    key = "@heartbeat"
    aliases = [
        "heartbeat",
        "@heartbeat/status",
        "@heartbeat/jobs",
        "@heartbeat/force",
        "@heartbeat/pause",
        "@heartbeat/resume",
    ]
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def _action(self) -> str:
        switches = {switch.lower() for switch in getattr(self, "switches", [])}
        for action in ("status", "jobs", "force", "pause", "resume"):
            if action in switches:
                return action
        arg = (getattr(self, "args", "") or "").strip().lower()
        return arg if arg in {"status", "jobs", "force", "pause", "resume"} else "status"

    def _script_for_mutation(self):
        return get_heartbeat_script() or ensure_heartbeat_script()

    def func(self):
        action = self._action()

        if action == "jobs":
            self.caller.msg(format_heartbeat_jobs())
            return

        if action == "status":
            self.caller.msg(format_heartbeat_status(get_heartbeat_script()))
            return

        script = self._script_for_mutation()
        if script is None:
            self.caller.msg("Heartbeat script is not available.")
            return

        if action == "pause":
            set_heartbeat_paused(script, True)
            self.caller.msg("Heartbeat paused.")
            return

        if action == "resume":
            set_heartbeat_paused(script, False)
            self.caller.msg("Heartbeat resumed.")
            return

        result = run_heartbeat_tick(script, forced=True)
        status = result.get("status", "unknown")
        tick_count = result.get("tick_count", "?")
        failures = result.get("failures") or []
        if failures:
            self.caller.msg(
                f"Heartbeat forced tick #{tick_count} completed with failures: "
                f"{'; '.join(failures)}"
            )
        else:
            self.caller.msg(f"Heartbeat forced tick #{tick_count} completed ({status}).")

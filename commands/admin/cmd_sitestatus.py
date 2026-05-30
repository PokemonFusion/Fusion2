"""Wizard command for setting the public play status."""

from __future__ import annotations

from evennia import Command

from utils.site_status import (
    VALID_STATUSES,
    clear_site_status,
    get_site_status,
    set_site_status,
)


class CmdSiteStatus(Command):
    """View or change the public play status.

    Usage:
      @sitestatus
      @sitestatus open [= message]
      @sitestatus limited [= message]
      @sitestatus maintenance [= message]
      @sitestatus clear
    """

    key = "@sitestatus"
    aliases = ["sitestatus"]
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def parse(self):
        """Split status and optional message."""

        raw = (self.args or "").strip()
        if "=" in raw:
            lhs, rhs = raw.split("=", 1)
            self.status_arg = lhs.strip().lower()
            self.message = rhs.strip()
        else:
            self.status_arg = raw.lower()
            self.message = None

    def _show_current(self):
        current = get_site_status()
        enabled = "enabled" if current.logins_enabled else "blocked for non-Wizards"
        self.caller.msg(
            f"Play status: {current.label} ({current.status}).\n"
            f"Message: {current.message}\n"
            f"Logins: {enabled}."
        )

    def func(self):
        """Display or update play status."""

        if not self.status_arg:
            self._show_current()
            return

        if self.status_arg == "clear":
            current = clear_site_status()
            self.caller.msg(f"Play status reset to {current.label}.")
            return

        if self.status_arg not in VALID_STATUSES:
            self.caller.msg(
                "Unknown play status. Use one of: "
                f"{', '.join(VALID_STATUSES)}, or clear."
            )
            return

        current = set_site_status(self.status_arg, self.message, changed_by=self.caller)
        self.caller.msg(f"Play status set to {current.label}: {current.message}")

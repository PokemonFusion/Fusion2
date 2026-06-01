from evennia import Command, SESSION_HANDLER
from evennia.accounts.models import AccountDB
from evennia.utils.evtable import EvTable

from utils.staff_roster import (
    StaffRosterError,
    build_staff_rows,
    clear_staff_note,
    is_staff_account,
    set_staff_duty,
    set_staff_note,
    staff_is_on_duty,
)


def _all_accounts():
    return list(AccountDB.objects.all())


def _caller_account(command):
    return getattr(command, "account", None) or getattr(command, "caller", None)


def _truthy_arg(raw):
    lowered = (raw or "").strip().lower()
    if lowered in {"on", "yes", "true", "available"}:
        return True
    if lowered in {"off", "no", "false", "away"}:
        return False
    return None


class CmdStaff(Command):
    """Show the public account-based staff roster.

    Usage:
      +staff
      +staff/duty [on||off]
      +staff/note <status>
      +staff/clear
    """

    key = "+staff"
    locks = "cmd:all()"
    help_category = "General"
    account_caller = True

    def func(self):
        switches = {switch.lower() for switch in getattr(self, "switches", []) or []}

        if "help" in switches or (self.args or "").strip().lower() in {"help", "#help"}:
            self.caller.msg("Usage: +staff | +staff/duty [on||off] | +staff/note <status> | +staff/clear")
            return

        if "duty" in switches:
            self._set_duty()
            return

        if "note" in switches:
            self._set_note()
            return

        if "clear" in switches:
            self._clear_note()
            return

        self._show_roster()

    def _require_staff_account(self):
        account = _caller_account(self)
        if not is_staff_account(account):
            raise StaffRosterError("Only staff can change staff roster status.")
        return account

    def _set_duty(self):
        try:
            account = self._require_staff_account()
        except StaffRosterError as err:
            self.caller.msg(str(err))
            return

        requested = _truthy_arg(self.args)
        if requested is None:
            requested = not staff_is_on_duty(account)
        set_staff_duty(account, requested)
        self.caller.msg(f"Staff duty status is now {'on' if requested else 'off'}.")

    def _set_note(self):
        try:
            account = self._require_staff_account()
        except StaffRosterError as err:
            self.caller.msg(str(err))
            return

        note = (self.args or "").strip()
        if not note:
            self.caller.msg("Usage: +staff/note <status>")
            return
        saved = set_staff_note(account, note)
        self.caller.msg(f"Staff note set to: {saved}")

    def _clear_note(self):
        try:
            account = self._require_staff_account()
        except StaffRosterError as err:
            self.caller.msg(str(err))
            return

        clear_staff_note(account)
        self.caller.msg("Staff note cleared.")

    def _show_roster(self):
        rows = build_staff_rows(_all_accounts(), SESSION_HANDLER.get_sessions())
        if not rows:
            self.caller.msg("No staff accounts are listed.")
            return

        table = EvTable("Account", "Role", "Status", "Note")
        for row in rows:
            table.add_row(row["name"], ", ".join(row["roles"]), row["status"], row["note"] or "-")
        self.caller.msg(f"Staff Roster:\n{table}")

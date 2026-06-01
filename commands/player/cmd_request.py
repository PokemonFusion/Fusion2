from evennia import Command
from evennia.utils.evtable import EvTable

import utils.support_requests as support_requests
from utils.staff_roster import is_staff_account


def _caller_account(command):
    return getattr(command, "account", None) or getattr(command, "caller", None)


def _caller_character(command):
    session = getattr(command, "session", None)
    get_puppet = getattr(session, "get_puppet", None)
    if callable(get_puppet):
        puppet = get_puppet()
        if puppet:
            return puppet

    obj = getattr(command, "obj", None)
    account = _caller_account(command)
    return None if obj is account else obj


def _request_id_and_note(raw: str) -> tuple[str, str]:
    parts = (raw or "").strip().split(None, 1)
    if not parts:
        return "", ""
    return parts[0], parts[1] if len(parts) > 1 else ""


def _preview(text: str, width: int = 52) -> str:
    clean = " ".join(str(text or "").split())
    if len(clean) <= width:
        return clean
    return f"{clean[: width - 3].rstrip()}..."


def _requester_label(request: dict) -> str:
    character = request.get("requester_character") or ""
    account = request.get("requester_account") or "Unknown"
    return f"{character} ({account})" if character else account


class CmdRequest(Command):
    """Submit and manage support requests.

    Usage:
      +request <message>
      +request/list
      +request/show <id>
      +request/close <id> [note]

    Staff:
      +request/queue [open||closed||all]
      +request/claim <id>
      +request/close <id> [note]

    Aliases:
      request, +req
    """

    key = "+request"
    aliases = ["request", "+req"]
    locks = "cmd:all()"
    help_category = "General"
    account_caller = True

    def func(self):
        account = _caller_account(self)
        switches = {switch.lower() for switch in getattr(self, "switches", []) or []}

        if "help" in switches or (self.args or "").strip().lower() in {"help", "#help"}:
            self._show_help()
            return

        if "list" in switches or "status" in switches:
            self._show_my_requests(account)
            return

        if "show" in switches or "read" in switches:
            self._show_request(account)
            return

        if "queue" in switches or "open" in switches:
            self._show_queue(account)
            return

        if "claim" in switches:
            self._claim_request(account)
            return

        if "close" in switches or "done" in switches:
            self._close_request(account)
            return

        args = (self.args or "").strip()
        if not args:
            if is_staff_account(account):
                self._show_queue(account)
            else:
                self._show_my_requests(account)
            return

        self._create_request(account, args)

    def _show_help(self):
        self.caller.msg(
            "Usage: +request <message> | +request/list | +request/show <id> | "
            "+request/close <id> [note]. Staff: +request/queue, +request/claim <id>."
        )

    def _create_request(self, account, text):
        try:
            request = support_requests.create_request(account, _caller_character(self), text)
        except support_requests.SupportRequestError as err:
            self.caller.msg(str(err))
            return

        self.caller.msg(f"Request #{request['id']} submitted. Staff will review it when available.")

    def _show_my_requests(self, account):
        rows = support_requests.list_requests(requester=account)
        if not rows:
            self.caller.msg("You have no support requests.")
            return
        self._show_table(rows, title="Your Support Requests", include_requester=False)

    def _show_queue(self, account):
        if not is_staff_account(account):
            self.caller.msg("Only staff can view the support request queue.")
            return

        selector = (self.args or "open").strip().lower()
        if selector in {"all", "#all"}:
            status = None
        elif selector in {"closed", "#closed"}:
            status = support_requests.CLOSED_STATUS
        else:
            status = support_requests.OPEN_STATUS

        rows = support_requests.list_requests(status=status)
        if not rows:
            self.caller.msg("No support requests found.")
            return
        title = "Support Request Queue" if status != support_requests.CLOSED_STATUS else "Closed Support Requests"
        self._show_table(rows, title=title, include_requester=True)

    def _show_request(self, account):
        request_id = (self.args or "").strip()
        if not request_id:
            self.caller.msg("Usage: +request/show <id>")
            return

        try:
            request = support_requests.get_request(request_id)
        except support_requests.SupportRequestError as err:
            self.caller.msg(str(err))
            return

        if not support_requests.can_view_request(request, account):
            self.caller.msg("You can only view your own support requests.")
            return

        lines = [
            f"Request #{request.get('id')} [{request.get('status', 'open')}]",
            f"From: {_requester_label(request)}",
            f"Created: {request.get('created_at') or '-'}",
        ]
        if request.get("location"):
            lines.append(f"Location: {request['location']}")
        if request.get("claimed_by"):
            lines.append(f"Claimed by: {request['claimed_by']}")
        if request.get("closed_by"):
            lines.append(f"Closed by: {request['closed_by']} at {request.get('closed_at') or '-'}")
        if request.get("close_note"):
            lines.append(f"Close note: {request['close_note']}")
        lines.append("")
        lines.append(request.get("text") or "")
        self.caller.msg("\n".join(lines))

    def _claim_request(self, account):
        request_id = (self.args or "").strip()
        if not request_id:
            self.caller.msg("Usage: +request/claim <id>")
            return

        try:
            request = support_requests.claim_request(request_id, account)
        except support_requests.SupportRequestError as err:
            self.caller.msg(str(err))
            return

        self.caller.msg(f"Request #{request['id']} claimed.")

    def _close_request(self, account):
        request_id, note = _request_id_and_note(self.args)
        if not request_id:
            self.caller.msg("Usage: +request/close <id> [note]")
            return

        try:
            request = support_requests.close_request(request_id, account, note=note)
        except support_requests.SupportRequestError as err:
            self.caller.msg(str(err))
            return

        self.caller.msg(f"Request #{request['id']} closed.")

    def _show_table(self, rows, title: str, include_requester: bool):
        headers = ["ID", "Status"]
        if include_requester:
            headers.append("Requester")
        headers.extend(["Claimed", "Updated", "Summary"])

        table = EvTable(*headers)
        for request in rows:
            values = [
                request.get("id"),
                request.get("status", "open"),
            ]
            if include_requester:
                values.append(_requester_label(request))
            values.extend(
                [
                    request.get("claimed_by") or "-",
                    request.get("updated_at") or request.get("created_at") or "-",
                    _preview(request.get("text", "")),
                ]
            )
            table.add_row(*values)
        self.caller.msg(f"{title}:\n{table}")

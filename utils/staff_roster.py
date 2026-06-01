"""Shared helpers for public staff roster display."""

from __future__ import annotations


STAFF_ROLE_ALIASES = {
    "Wizards": ("Wizards", "Wizard"),
    "Developer": ("Developer", "Developers"),
    "Admin": ("Admin", "Admins"),
    "Builder": ("Builder", "Builders"),
    "Validator": ("Validator", "Validators"),
    "Helper": ("Helper", "Helpers"),
}
STAFF_NOTE_ATTR = "staff_note"
STAFF_DUTY_ATTR = "staff_duty"
MAX_STAFF_NOTE_LENGTH = 80


class StaffRosterError(ValueError):
    """Raised when a staff roster operation cannot be completed."""


def account_name(account) -> str:
    """Return a stable account display name."""

    return (
        getattr(account, "key", None)
        or getattr(account, "username", None)
        or getattr(account, "name", None)
        or str(account)
    )


def account_id(account):
    """Return a comparable account identity."""

    return getattr(account, "id", None) or getattr(account, "dbref", None) or account_name(account)


def account_permissions(account) -> set[str]:
    """Return directly assigned account permissions as strings."""

    permissions = getattr(account, "permissions", None)
    all_permissions = getattr(permissions, "all", None)
    if callable(all_permissions):
        try:
            return {str(perm) for perm in all_permissions() if perm}
        except Exception:
            return set()
    return set()


def staff_roles_for_account(account) -> list[str]:
    """Return public staff roles directly assigned to ``account``."""

    if getattr(account, "is_superuser", False):
        return ["Wizards"]

    assigned = account_permissions(account)
    roles = []
    for label, aliases in STAFF_ROLE_ALIASES.items():
        if any(alias in assigned for alias in aliases):
            roles.append(label)
    return roles


def is_staff_account(account) -> bool:
    """Return whether ``account`` should appear on the public staff roster."""

    return bool(staff_roles_for_account(account))


def account_is_online(account, sessions) -> bool:
    """Return whether any session currently belongs to ``account``."""

    target_id = account_id(account)
    for session in sessions:
        get_account = getattr(session, "get_account", None)
        session_account = get_account() if callable(get_account) else getattr(session, "account", None)
        if session_account and account_id(session_account) == target_id:
            return True
    return False


def staff_note(account) -> str:
    """Return the account's public staff note."""

    db = getattr(account, "db", None)
    note = getattr(db, STAFF_NOTE_ATTR, "") if db is not None else ""
    return str(note or "").strip()


def staff_is_on_duty(account) -> bool:
    """Return the account's duty flag, defaulting to available."""

    db = getattr(account, "db", None)
    value = getattr(db, STAFF_DUTY_ATTR, None) if db is not None else None
    return True if value is None else bool(value)


def set_staff_duty(account, on_duty: bool) -> bool:
    """Persist the account's duty flag."""

    account.db.staff_duty = bool(on_duty)
    return bool(on_duty)


def set_staff_note(account, note: str) -> str:
    """Persist a short public staff note."""

    cleaned = " ".join(str(note or "").split())
    if len(cleaned) > MAX_STAFF_NOTE_LENGTH:
        cleaned = cleaned[:MAX_STAFF_NOTE_LENGTH].rstrip()
    account.db.staff_note = cleaned
    return cleaned


def clear_staff_note(account) -> None:
    """Clear the account's public staff note."""

    account.db.staff_note = ""


def staff_status(account, online: bool) -> str:
    """Return the public roster status for ``account``."""

    if not staff_is_on_duty(account):
        return "Off duty"
    return "Online" if online else "Offline"


def build_staff_rows(accounts, sessions) -> list[dict]:
    """Build display rows for public staff roster output."""

    rows = []
    for account in accounts:
        roles = staff_roles_for_account(account)
        if not roles:
            continue
        online = account_is_online(account, sessions)
        rows.append(
            {
                "account": account,
                "name": account_name(account),
                "roles": roles,
                "status": staff_status(account, online),
                "online": online,
                "note": staff_note(account),
            }
        )

    return sorted(rows, key=lambda row: (not row["online"], row["name"].lower()))

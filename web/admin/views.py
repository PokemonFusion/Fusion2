"""Custom web admin views for Fusion2."""

from __future__ import annotations

from django.shortcuts import render

from evennia.accounts.models import AccountDB

from .access import account_roster_required


def _as_list(value) -> list:
    """Return ``value`` as a list while tolerating unavailable managers."""

    if value is None:
        return []
    try:
        if hasattr(value, "all"):
            value = value.all()
        return list(value)
    except Exception:
        return []


def _display_name(obj) -> str:
    return (
        getattr(obj, "key", None)
        or getattr(obj, "username", None)
        or getattr(obj, "name", None)
        or str(obj)
    )


def _dbref(obj) -> str:
    dbref = getattr(obj, "dbref", None)
    if dbref:
        return str(dbref)
    ident = getattr(obj, "id", None) or getattr(obj, "pk", None)
    return f"#{ident}" if ident is not None else ""


def _datetime_label(value) -> str:
    if not value:
        return ""
    formatter = getattr(value, "strftime", None)
    if callable(formatter):
        return formatter("%Y-%m-%d %H:%M")
    return str(value)


def _short_typeclass(obj) -> str:
    path = getattr(obj, "typeclass_path", None) or getattr(obj, "db_typeclass_path", None) or ""
    return str(path).split(".")[-1] if path else ""


def _account_permissions(account) -> list[str]:
    labels = []
    if getattr(account, "is_superuser", False):
        labels.append("Wizard")

    permissions = getattr(account, "permissions", None)
    all_permissions = getattr(permissions, "all", None)
    if callable(all_permissions):
        try:
            labels.extend(str(permission) for permission in all_permissions() if permission)
        except Exception:
            pass

    return sorted(dict.fromkeys(labels), key=str.lower)


def _character_row(character) -> dict:
    location = getattr(character, "location", None) or getattr(character, "db_location", None)
    sessions = getattr(character, "sessions", None)
    return {
        "name": _display_name(character),
        "dbref": _dbref(character),
        "location": _display_name(location) if location else "",
        "typeclass": _short_typeclass(character),
        "online": bool(_as_list(sessions)),
    }


def _account_characters(account) -> list[dict]:
    try:
        characters = account.characters
    except Exception:
        characters = []
    return [_character_row(character) for character in _as_list(characters) if character]


def _account_row(account) -> dict:
    characters = _account_characters(account)
    return {
        "name": _display_name(account),
        "dbref": _dbref(account),
        "roles": _account_permissions(account),
        "created": _datetime_label(
            getattr(account, "date_joined", None) or getattr(account, "date_created", None)
        ),
        "last_login": _datetime_label(getattr(account, "last_login", None)),
        "characters": characters,
        "character_count": len(characters),
    }


def _row_matches(row: dict, query: str) -> bool:
    if not query:
        return True

    lowered = query.lower()
    values = [row["name"], row["dbref"], *row["roles"]]
    for character in row["characters"]:
        values.extend(
            [
                character["name"],
                character["dbref"],
                character["location"],
                character["typeclass"],
            ]
        )
    return any(lowered in str(value).lower() for value in values if value)


def _all_accounts():
    accounts = AccountDB.objects.all()
    order_by = getattr(accounts, "order_by", None)
    if callable(order_by):
        try:
            accounts = order_by("username")
        except Exception:
            pass
    return accounts


def build_account_roster(accounts=None) -> list[dict]:
    """Build account/character rows for the roster page."""

    rows = [_account_row(account) for account in _as_list(_all_accounts() if accounts is None else accounts)]
    return sorted(rows, key=lambda row: row["name"].lower())


def filter_account_roster(rows: list[dict], query: str) -> list[dict]:
    """Return roster rows matching ``query``."""

    cleaned = (query or "").strip()
    return [row for row in rows if _row_matches(row, cleaned)]


@account_roster_required
def player_roster(request):
    """Display accounts with their playable character rosters."""

    query = (request.GET.get("q") or "").strip()
    all_rows = build_account_roster()
    rows = filter_account_roster(all_rows, query)
    context = {
        "page_title": "Player Account Roster",
        "query": query,
        "rows": rows,
        "account_count": len(all_rows),
        "character_count": sum(row["character_count"] for row in all_rows),
        "displayed_account_count": len(rows),
        "displayed_character_count": sum(row["character_count"] for row in rows),
    }
    return render(request, "admin/player_roster.html", context)

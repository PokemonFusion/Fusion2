"""Persistent support request queue helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from utils.staff_roster import account_id, account_name, is_staff_account


REQUESTS_CONFIG_KEY = "fusion2_support_requests"
MAX_REQUEST_TEXT_LENGTH = 1200
MAX_REQUEST_NOTE_LENGTH = 300
OPEN_STATUS = "open"
CLOSED_STATUS = "closed"


class SupportRequestError(ValueError):
    """Raised when a support request operation cannot be completed."""


def _server_config():
    """Return Evennia's ServerConfig model lazily for testability."""

    from evennia.server.models import ServerConfig

    return ServerConfig


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clean_text(text: str, max_length: int = MAX_REQUEST_TEXT_LENGTH) -> str:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip()
    return cleaned


def _character_name(character) -> str:
    if not character:
        return ""
    return getattr(character, "key", None) or getattr(character, "name", None) or str(character)


def _character_id(character):
    if not character:
        return None
    return getattr(character, "id", None) or getattr(character, "dbref", None)


def _location_name(character) -> str:
    location = getattr(character, "location", None)
    if not location:
        return ""
    return getattr(location, "key", None) or getattr(location, "name", None) or str(location)


def load_requests() -> list[dict]:
    """Return all stored support requests."""

    raw = _server_config().objects.conf(REQUESTS_CONFIG_KEY, default=[])
    if not isinstance(raw, list):
        return []
    return [dict(item) for item in raw if isinstance(item, dict)]


def save_requests(requests: list[dict]) -> list[dict]:
    """Persist support requests and return a normalized list."""

    normalized = [dict(item) for item in requests if isinstance(item, dict)]
    _server_config().objects.conf(REQUESTS_CONFIG_KEY, normalized)
    return normalized


def clear_requests() -> None:
    """Remove all stored support requests."""

    _server_config().objects.conf(REQUESTS_CONFIG_KEY, delete=True)


def _next_request_id(requests: list[dict]) -> int:
    ids = []
    for request in requests:
        try:
            ids.append(int(request.get("id", 0)))
        except (TypeError, ValueError):
            continue
    return (max(ids) if ids else 0) + 1


def _same_account(request: dict, account) -> bool:
    if not account:
        return False

    stored_id = request.get("requester_account_id")
    current_id = account_id(account)
    if stored_id is not None and current_id is not None and str(stored_id) == str(current_id):
        return True
    return str(request.get("requester_account", "")).lower() == account_name(account).lower()


def create_request(account, character, text: str) -> dict:
    """Create a new open support request."""

    clean = _clean_text(text)
    if not clean:
        raise SupportRequestError("Usage: +request <message>")

    requests = load_requests()
    timestamp = _now()
    request = {
        "id": _next_request_id(requests),
        "status": OPEN_STATUS,
        "requester_account": account_name(account),
        "requester_account_id": account_id(account),
        "requester_character": _character_name(character),
        "requester_character_id": _character_id(character),
        "location": _location_name(character),
        "text": clean,
        "created_at": timestamp,
        "updated_at": timestamp,
        "claimed_by": "",
        "claimed_by_id": None,
        "closed_by": "",
        "closed_by_id": None,
        "closed_at": "",
        "close_note": "",
    }
    requests.append(request)
    save_requests(requests)
    return request


def list_requests(status: str | None = None, requester=None) -> list[dict]:
    """Return requests filtered by optional status and requester account."""

    rows = load_requests()
    if status:
        rows = [request for request in rows if request.get("status") == status]
    if requester:
        rows = [request for request in rows if _same_account(request, requester)]
    return sorted(rows, key=lambda request: int(request.get("id", 0)), reverse=True)


def get_request(request_id: int | str) -> dict:
    """Return a single support request by id."""

    try:
        needle = int(request_id)
    except (TypeError, ValueError):
        raise SupportRequestError("Request id must be a number.")

    for request in load_requests():
        try:
            if int(request.get("id", 0)) == needle:
                return request
        except (TypeError, ValueError):
            continue
    raise SupportRequestError(f"No request #{needle} found.")


def _update_request(request_id: int | str, updater) -> dict:
    try:
        needle = int(request_id)
    except (TypeError, ValueError):
        raise SupportRequestError("Request id must be a number.")

    requests = load_requests()
    for index, request in enumerate(requests):
        try:
            matched = int(request.get("id", 0)) == needle
        except (TypeError, ValueError):
            matched = False
        if not matched:
            continue

        updated = dict(request)
        updater(updated)
        updated["updated_at"] = _now()
        requests[index] = updated
        save_requests(requests)
        return updated

    raise SupportRequestError(f"No request #{needle} found.")


def claim_request(request_id: int | str, staff_account) -> dict:
    """Assign an open request to a staff account."""

    if not is_staff_account(staff_account):
        raise SupportRequestError("Only staff can claim support requests.")

    def updater(request):
        if request.get("status") == CLOSED_STATUS:
            raise SupportRequestError(f"Request #{request.get('id')} is already closed.")
        request["claimed_by"] = account_name(staff_account)
        request["claimed_by_id"] = account_id(staff_account)

    return _update_request(request_id, updater)


def close_request(request_id: int | str, closer, note: str = "") -> dict:
    """Close a support request as staff or as its original requester."""

    request = get_request(request_id)
    staff = is_staff_account(closer)
    if not staff and not _same_account(request, closer):
        raise SupportRequestError("You can only close your own support requests.")

    def updater(request):
        if request.get("status") == CLOSED_STATUS:
            raise SupportRequestError(f"Request #{request.get('id')} is already closed.")
        request["status"] = CLOSED_STATUS
        request["closed_by"] = account_name(closer)
        request["closed_by_id"] = account_id(closer)
        request["closed_at"] = _now()
        request["close_note"] = _clean_text(note, MAX_REQUEST_NOTE_LENGTH)

    return _update_request(request_id, updater)


def can_view_request(request: dict, account) -> bool:
    """Return whether an account can read a support request."""

    return is_staff_account(account) or _same_account(request, account)

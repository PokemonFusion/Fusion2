"""Runtime play-status helpers for the website and login flow."""

from __future__ import annotations

from dataclasses import dataclass

STATUS_OPEN = "open"
STATUS_LIMITED = "limited"
STATUS_MAINTENANCE = "maintenance"

VALID_STATUSES = (STATUS_OPEN, STATUS_LIMITED, STATUS_MAINTENANCE)

STATUS_CONFIG_KEY = "fusion2_site_status"
MESSAGE_CONFIG_KEY = "fusion2_site_status_message"

DEFAULT_MESSAGES = {
    STATUS_OPEN: "The world is ready.",
    STATUS_LIMITED: "Some services may be unavailable.",
    STATUS_MAINTENANCE: "Logins are paused while updates are applied.",
}

STATUS_LABELS = {
    STATUS_OPEN: "Open",
    STATUS_LIMITED: "Limited",
    STATUS_MAINTENANCE: "Maintenance",
}


@dataclass(frozen=True)
class SiteStatus:
    """Display-ready state shared by the homepage and login enforcement."""

    status: str
    label: str
    message: str
    css_class: str
    logins_enabled: bool


def _server_config():
    """Return Evennia's ServerConfig model lazily for testability."""

    from evennia.server.models import ServerConfig

    return ServerConfig


def normalize_status(status: str | None) -> str:
    """Return a canonical status or raise ``ValueError`` for unknown values."""

    normalized = (status or STATUS_OPEN).strip().lower()
    if normalized not in VALID_STATUSES:
        allowed = ", ".join(VALID_STATUSES)
        raise ValueError(f"Unknown site status '{status}'. Expected one of: {allowed}.")
    return normalized


def get_site_status() -> SiteStatus:
    """Load the current play status from persistent ServerConfig storage."""

    config = _server_config()
    raw_status = config.objects.conf(STATUS_CONFIG_KEY, default=STATUS_OPEN)
    try:
        status = normalize_status(raw_status)
    except ValueError:
        status = STATUS_OPEN

    custom_message = config.objects.conf(MESSAGE_CONFIG_KEY, default="")
    message = (custom_message or "").strip() or DEFAULT_MESSAGES[status]
    return SiteStatus(
        status=status,
        label=STATUS_LABELS[status],
        message=message,
        css_class=status,
        logins_enabled=status != STATUS_MAINTENANCE,
    )


def set_site_status(status: str, message: str | None = None, changed_by=None) -> SiteStatus:
    """Persist a new play status and optional display/login message."""

    normalized = normalize_status(status)
    config = _server_config()
    config.objects.conf(STATUS_CONFIG_KEY, normalized)

    clean_message = (message or "").strip()
    if clean_message:
        config.objects.conf(MESSAGE_CONFIG_KEY, clean_message)
    else:
        config.objects.conf(MESSAGE_CONFIG_KEY, delete=True)

    return get_site_status()


def clear_site_status() -> SiteStatus:
    """Reset play status to open and clear any custom message."""

    config = _server_config()
    config.objects.conf(STATUS_CONFIG_KEY, delete=True)
    config.objects.conf(MESSAGE_CONFIG_KEY, delete=True)
    return get_site_status()


def is_wizard(account) -> bool:
    """Return whether an account should bypass maintenance login blocks."""

    if not account:
        return False
    permissions = getattr(account, "permissions", None)
    check = getattr(permissions, "check", None)
    return bool(check and check("Wizards"))


def is_login_blocked(account) -> bool:
    """Return ``True`` when the current status should reject this login."""

    status = get_site_status()
    return status.status == STATUS_MAINTENANCE and not is_wizard(account)


def get_login_block_message() -> str:
    """Return the current message to show when login is blocked."""

    return get_site_status().message

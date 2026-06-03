"""Editable landing-page announcement state."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from utils.staff_roster import account_name

ANNOUNCEMENT_CONFIG_KEY = "fusion2_landing_announcement"

DEFAULT_LABEL = "RECENT WORLD NEWS"
DEFAULT_TITLE = "Development Server Notes"
DEFAULT_BODY = (
    "Fusion 2 is actively evolving. Expect balance passes, route updates, and "
    "trainer-facing improvements while the test server takes shape."
)
DEFAULT_BULLETS = (
    "Browser play is the primary way to jump into the world.",
    "The Player Hub exposes roster, inventory, badges, and trainer progress from the website.",
    "Builder tools remain available for staff through the Room Editor.",
)

_MISSING = object()
_WHITESPACE_RE = re.compile(r"[ \t\r\f\v]+")


@dataclass(frozen=True)
class LandingAnnouncement:
    """Display-ready landing-page announcement."""

    label: str
    title: str
    body: str
    bullets: tuple[str, ...]
    visible: bool
    updated_at: str
    updated_by: str
    is_default: bool = False

    @property
    def body_paragraphs(self) -> tuple[str, ...]:
        """Return simple paragraph blocks for safe template rendering."""

        paragraphs = []
        for paragraph in re.split(r"\n\s*\n", self.body.strip()):
            cleaned = _clean_multiline(paragraph).strip()
            if cleaned:
                paragraphs.append(cleaned)
        return tuple(paragraphs)


def _server_config():
    """Return Evennia's ServerConfig model lazily for testability."""

    from evennia.server.models import ServerConfig

    return ServerConfig


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _clean_single_line(value: Any, default: str = "") -> str:
    cleaned = _WHITESPACE_RE.sub(" ", str(value or "")).strip()
    return cleaned or default


def _clean_multiline(value: Any) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [_WHITESPACE_RE.sub(" ", line).strip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def _clean_bullets(values: Any) -> tuple[str, ...]:
    if isinstance(values, str):
        values = values.splitlines()
    elif isinstance(values, Iterable):
        values = list(values)
    else:
        return ()
    return tuple(_clean_single_line(value) for value in values if _clean_single_line(value))


def _actor_name(actor) -> str:
    if actor is None:
        return ""
    account = getattr(actor, "account", None) or actor
    return account_name(account)


def _default_data() -> dict[str, Any]:
    return {
        "label": DEFAULT_LABEL,
        "title": DEFAULT_TITLE,
        "body": DEFAULT_BODY,
        "bullets": list(DEFAULT_BULLETS),
        "visible": True,
        "updated_at": "",
        "updated_by": "",
    }


def _read_data() -> tuple[dict[str, Any], bool]:
    raw = _server_config().objects.conf(ANNOUNCEMENT_CONFIG_KEY, default=None)
    if not isinstance(raw, Mapping):
        return _default_data(), True

    data = _default_data()
    data.update(dict(raw))
    return data, False


def _to_announcement(data: dict[str, Any], *, is_default: bool) -> LandingAnnouncement:
    return LandingAnnouncement(
        label=_clean_single_line(data.get("label"), DEFAULT_LABEL),
        title=_clean_single_line(data.get("title"), DEFAULT_TITLE),
        body=_clean_multiline(data.get("body")) or DEFAULT_BODY,
        bullets=_clean_bullets(data.get("bullets")),
        visible=bool(data.get("visible", True)),
        updated_at=_clean_single_line(data.get("updated_at")),
        updated_by=_clean_single_line(data.get("updated_by")),
        is_default=is_default,
    )


def get_landing_announcement() -> LandingAnnouncement:
    """Load the landing announcement, falling back to default content."""

    data, is_default = _read_data()
    return _to_announcement(data, is_default=is_default)


def update_landing_announcement(
    *,
    label: Any = _MISSING,
    title: Any = _MISSING,
    body: Any = _MISSING,
    bullets: Any = _MISSING,
    visible: bool | object = _MISSING,
    changed_by=None,
) -> LandingAnnouncement:
    """Persist updates to the landing announcement."""

    data, _ = _read_data()
    if label is not _MISSING:
        data["label"] = _clean_single_line(label, DEFAULT_LABEL)
    if title is not _MISSING:
        data["title"] = _clean_single_line(title, DEFAULT_TITLE)
    if body is not _MISSING:
        data["body"] = _clean_multiline(body) or DEFAULT_BODY
    if bullets is not _MISSING:
        data["bullets"] = list(_clean_bullets(bullets))
    if visible is not _MISSING:
        data["visible"] = bool(visible)

    data["updated_at"] = _now_iso()
    data["updated_by"] = _actor_name(changed_by)
    _server_config().objects.conf(ANNOUNCEMENT_CONFIG_KEY, data)
    return get_landing_announcement()


def add_landing_bullet(text: str, *, changed_by=None) -> LandingAnnouncement:
    """Append one bullet to the landing announcement."""

    current = get_landing_announcement()
    bullet = _clean_single_line(text)
    if not bullet:
        raise ValueError("Bullet text cannot be empty.")
    return update_landing_announcement(
        bullets=[*current.bullets, bullet],
        changed_by=changed_by,
    )


def clear_landing_bullets(*, changed_by=None) -> LandingAnnouncement:
    """Remove all landing announcement bullets."""

    return update_landing_announcement(bullets=[], changed_by=changed_by)


def reset_landing_announcement() -> LandingAnnouncement:
    """Remove custom landing announcement state."""

    _server_config().objects.conf(ANNOUNCEMENT_CONFIG_KEY, delete=True)
    return get_landing_announcement()

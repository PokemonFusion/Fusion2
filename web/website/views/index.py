"""Project-owned homepage view with Fusion 2 play status context."""

from __future__ import annotations

import re

from evennia.web.website.views.index import EvenniaIndexView

from utils.landing_announcement import get_landing_announcement
from utils.site_status import get_site_status

WEBCLIENT_PREVIEW_COMMANDS = ("look", "map", "party", "sheet", "inventory", "help")
_ANSI_TOKEN_RE = re.compile(r"(\|[a-zA-Z])")
_ANSI_TOKEN_CLASSES = {
    "|b": "ansi-blue",
    "|g": "ansi-green",
    "|r": "ansi-red",
    "|w": "ansi-white",
    "|x": "ansi-gray",
    "|y": "ansi-yellow",
}


def _strip_evennia_ansi(text: str) -> str:
    """Remove Evennia ANSI markers from a single display line."""

    return _ANSI_TOKEN_RE.sub("", text)


def _ansi_segments(line: str) -> list[dict[str, str]]:
    """Split an Evennia ANSI-marked line into CSS-ready template segments."""

    segments: list[dict[str, str]] = []
    active_class = ""
    cursor = 0

    for match in _ANSI_TOKEN_RE.finditer(line):
        if match.start() > cursor:
            segments.append({"text": line[cursor : match.start()], "class": active_class})

        token = match.group(1)
        if token == "|n":
            active_class = ""
        elif token in _ANSI_TOKEN_CLASSES:
            active_class = _ANSI_TOKEN_CLASSES[token]
        cursor = match.end()

    if cursor < len(line):
        segments.append({"text": line[cursor:], "class": active_class})

    return segments or [{"text": " ", "class": ""}]


def build_webclient_preview_lines(connection_screen: str | None = None) -> list[list[dict[str, str]]]:
    """Return a compact splash excerpt for the homepage webclient preview."""

    if connection_screen is None:
        from server.conf.connection_screens import CONNECTION_SCREEN

        connection_screen = CONNECTION_SCREEN

    selected: list[str] = []
    for raw_line in connection_screen.splitlines():
        if not raw_line.strip():
            continue

        visible = _strip_evennia_ansi(raw_line).strip()
        if visible.startswith("If "):
            break

        selected.append(raw_line.rstrip())
        if visible.startswith("Welcome to "):
            break

    return [_ansi_segments(line) for line in selected]


class Fusion2IndexView(EvenniaIndexView):
    """Homepage view preserving Evennia stats and adding play status."""

    def get_context_data(self, **kwargs):
        """Add display-ready play status to the standard index context."""

        context = super().get_context_data(**kwargs)
        status = get_site_status()
        context.update(
            {
                "site_status": status.status,
                "site_status_label": status.label,
                "site_status_message": status.message,
                "site_status_class": status.css_class,
                "site_logins_enabled": status.logins_enabled,
                "landing_announcement": get_landing_announcement(),
                "webclient_preview_commands": WEBCLIENT_PREVIEW_COMMANDS,
                "webclient_preview_lines": build_webclient_preview_lines(),
            }
        )
        return context

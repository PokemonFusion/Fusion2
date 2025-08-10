"""Rendering helpers for battle user interfaces."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# Matches Either |X where X is letter, or |[123] style codes
ANSI_RE = re.compile(r"\|\[[0-9]{1,3}\]|\|[A-Za-z]")


def strip_ansi(s: str) -> str:
    """Remove Evennia-style ANSI codes."""

    return ANSI_RE.sub("", s)


def pad_ansi(s: str, width: int) -> str:
    """Pad ``s`` with spaces up to ``width`` visible characters."""

    visible = len(strip_ansi(s))
    return s + " " * max(0, width - visible)


def fit_visible(text: str, maxw: int) -> str:
    """Truncate ``text`` to at most ``maxw`` visible characters."""

    vis = strip_ansi(text)
    if len(vis) <= maxw:
        return text
    short = vis[: max(0, maxw - 1)] + "…"
    return short


def render_move_gui(
    slots: List[Any],
    pp_overrides: Optional[Dict[int, int]] = None,
    total_width: int = 76,
) -> str:
    """Proxy to :func:`pokemon.ui.move_gui.render_move_gui`."""

    from pokemon.ui.move_gui import render_move_gui as _render

    return _render(slots, pp_overrides=pp_overrides, total_width=total_width)


def render_battle_ui(state, viewer, total_width: int = 100, waiting_on=None) -> str:
    """Proxy to :func:`pokemon.ui.battle_render.render_battle_ui`.

    Parameters mirror :func:`pokemon.ui.battle_render.render_battle_ui` with
    the addition of ``waiting_on`` which allows rendering a waiting indicator
    in the footer.
    """

    from pokemon.ui.battle_render import render_battle_ui as _render

    return _render(state, viewer, total_width=total_width, waiting_on=waiting_on)


__all__ = [
    "strip_ansi",
    "pad_ansi",
    "fit_visible",
    "render_move_gui",
    "render_battle_ui",
]


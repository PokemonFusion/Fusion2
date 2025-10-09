"""Reusable ANSI-friendly widget helpers for trainer and Pokémon sheets."""

from __future__ import annotations

from typing import Iterable, Sequence

from evennia.utils import ansi as _ansi
from evennia.utils import utils as _utils

__all__ = [
        "header_box",
        "kv_row",
        "bar",
        "chip",
        "join_items",
        "money_line",
        "infer_hp_phrase",
        "infer_xp_phrase",
]


def _strip_ansi(text: str) -> str:
        """Return ``text`` with ANSI codes removed using available helpers."""

        if hasattr(_utils, "strip_ansi"):
                return _utils.strip_ansi(text)
        return _ansi.strip_ansi(text)


def _strip_ansi_len(text: str) -> int:
        """Return the visible length of ``text`` with ANSI codes removed."""

        return len(_strip_ansi(text))


def _ansi_pad(text: str, width: int, align: str = "left") -> str:
        """Return ``text`` padded to ``width`` characters, ignoring ANSI codes."""

        visible = _strip_ansi_len(text)
        pad = max(0, width - visible)
        if align == "right":
                return " " * pad + text
        if align == "center":
                left = pad // 2
                right = pad - left
                return " " * left + text + " " * right
        return text + " " * pad


def header_box(title: str, left: str = "", right: str = "", width: int = 60) -> str:
        """Return a two-line header box with ANSI-aware padding."""

        inner_width = max(4, width - 2)
        top = f"┌{'─' * inner_width}┐"
        bottom = f"└{'─' * inner_width}┘"

        left = left or ""
        right = right or ""
        left_visible = _strip_ansi_len(left)
        right_visible = _strip_ansi_len(right)
        space = max(0, inner_width - left_visible - right_visible)
        name_line = f"│{left}{' ' * space}{right}│"

        title = title or ""
        title_content = _ansi_pad(title, inner_width, align="center")
        title_line = f"│{title_content}│"

        return "\n".join((top, name_line, title_line, bottom))


def kv_row(k1: str, v1: str, k2: str | None = None, v2: str | None = None, *, width: int = 60, keyw: int = 12) -> str:
        """Return a pair of key/value fields padded for a consistent layout."""

        col_width = (width - 2) // 2
        left_key = f"{k1}:".ljust(keyw + 1)
        left = f"{left_key} {v1}".rstrip()
        if not k2:
                return left

        right_key = f"{k2}:".ljust(keyw + 1)
        right = f"{right_key} {v2}".rstrip()

        left = _ansi_pad(left, col_width)
        return f"{left}  {right}"


def bar(now: int, maximum: int, width: int = 16) -> str:
        """Return a colored progress bar for ``now``/``maximum`` values."""

        if maximum <= 0:
                return "|w[{}]|n".format("-" * width)

        ratio = max(0.0, min(1.0, float(now) / float(maximum)))
        filled = int(round(ratio * width))
        filled = max(0, min(width, filled))
        if ratio >= 0.66:
                color = "|G"
        elif ratio >= 0.33:
                color = "|y"
        else:
                color = "|r"
        fill = "█" * filled
        empty = "-" * (width - filled)
        if fill:
                return f"|w[|n{color}{fill}|n|w{empty}]|n"
        return f"|w[|n{empty}]|n"


def chip(text: str, color: str = "|y") -> str:
        """Return ``text`` wrapped in a simple colored chip."""

        return f"|w[|n{color}{text}|n|w]|n"


def infer_hp_phrase(now: int, maximum: int) -> str:
        """Return a qualitative description of HP remaining."""

        if maximum <= 0:
                return "Unknown"
        ratio = now / maximum
        if ratio >= 0.95:
                return "Full"
        if ratio >= 0.70:
                return "High"
        if ratio >= 0.40:
                return "Mid"
        if ratio >= 0.15:
                return "Low"
        return "Critical"


def infer_xp_phrase(to_next: int) -> str:
        """Return a qualitative description of XP progress."""

        if to_next <= 0:
                return "Ready to level"
        if to_next < 100:
                return "Nearly there"
        if to_next < 300:
                return "Making progress"
        return "Just getting started"


def join_items(pairs: Iterable[tuple[str, int]] | Sequence[tuple[str, int]], *, max_items: int = 5) -> str:
        """Return a friendly chip list summarising ``pairs`` of (name, count)."""

        normalized: list[tuple[str, int]] = []
        for name, count in pairs or []:
                try:
                        normalized.append((str(name), int(count)))
                except Exception:
                        normalized.append((str(name), 1))
        if not normalized:
                return ""
        normalized.sort(key=lambda item: (-item[1], item[0]))
        shown = [chip(f"{name} × {count}", "|y") for name, count in normalized[:max_items]]
        remaining = len(normalized) - len(shown)
        if remaining > 0:
                shown.append(chip(f"+{remaining} more…", "|x"))
        return " ".join(shown)


def money_line(wallet, bank=None) -> str:
        """Return a chip summary for wallet/bank style balances."""

        def _fmt(value):
                if value is None:
                        return "Unknown"
                if isinstance(value, (int, float)):
                        return f"₽ {int(value):,}"
                try:
                        return f"₽ {int(value):,}"
                except (TypeError, ValueError):
                        return str(value)

        parts = []
        parts.append(chip(f"Wallet {_fmt(wallet)}", "|G"))
        if bank is not None:
                parts.append(chip(f"Bank {_fmt(bank)}", "|c"))
        return " ".join(parts)

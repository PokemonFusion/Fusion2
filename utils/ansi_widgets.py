"""Reusable ANSI-friendly widget helpers for trainer and Pokémon sheets.

This module centralises the small formatting helpers that different sheet
renderers use.  All helpers are ANSI aware and provide sensible fallbacks for
older Evennia versions that expose the ANSI stripping utilities in different
modules.

The new theme helpers expose a lightweight colour palette that can be reused
across displays.  Call-sites can either import :data:`THEME` directly or use
the :func:`get_theme` helper to safely merge overrides without mutating the
module level defaults.
"""

from __future__ import annotations

from typing import Iterable, Mapping, MutableMapping, Sequence

from evennia.utils import ansi as _ansi
from evennia.utils import utils as _utils

__all__ = [
        "DEFAULT_THEME",
        "THEME",
        "apply_screen_reader",
        "bar",
        "chip",
        "format_currency",
        "get_theme",
        "header_box",
        "infer_hp_phrase",
        "infer_xp_phrase",
        "join_items",
        "kv_row",
        "money_line",
        "section_divider",
        "stat_summary_row",
        "status_code",
        "themed_line",
        "type_chip",
]


def _strip_ansi(text: str) -> str:
        """Return ``text`` with ANSI codes removed using available helpers."""

        if hasattr(_utils, "strip_ansi"):
                return _utils.strip_ansi(text)
        return _ansi.strip_ansi(text)


def _strip_ansi_len(text: str) -> int:
        """Return the visible length of ``text`` with ANSI codes removed."""

        return len(_strip_ansi(text))


def apply_screen_reader(text: str) -> str:
        """Return ``text`` with ANSI codes removed for screen readers."""

        return _strip_ansi(text)


DEFAULT_THEME: Mapping[str, str] = {
        "border": "|g",
        "label": "|y",
        "value": "|W",
        "muted": "|x",
        "ok": "|G",
        "warn": "|y",
        "bad": "|r",
        "type": "|c",
}


THEME: MutableMapping[str, str] = dict(DEFAULT_THEME)


def get_theme(overrides: Mapping[str, str] | None = None) -> dict[str, str]:
        """Return a copy of the active theme optionally merged with overrides."""

        palette = dict(THEME)
        if overrides:
                palette.update(overrides)
        return palette


def themed_line(char: str = "─", width: int = 60, *, theme: Mapping[str, str] | None = None,
                screen_reader: bool = False) -> str:
        """Return a horizontal line using the active theme."""

        fill = (char or "─") * max(0, width)
        if screen_reader:
                return fill.replace("─", "-")
        palette = get_theme(theme)
        return f"{palette['border']}{fill}|n"


def section_divider(title: str, width: int = 60, *, theme: Mapping[str, str] | None = None,
                    screen_reader: bool = False) -> str:
        """Return a labeled divider for separating sheet sections."""

        clean_title = title.strip() if title else ""
        if screen_reader:
                pad = max(0, width - len(clean_title) - 2)
                return f"-- {clean_title} {'-' * pad}".rstrip()

        palette = get_theme(theme)
        visible = _strip_ansi_len(clean_title)
        pad = max(0, width - visible - 4)
        line = "─" * pad
        return f"{palette['border']}┤|n {palette['label']}{clean_title}|n {palette['border']}├{line}|n"


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


def header_box(title: str, left: str = "", right: str = "", width: int = 60,
               *, theme: Mapping[str, str] | None = None,
               screen_reader: bool = False) -> str:
        """Return a two-line header box with ANSI-aware padding."""

        if screen_reader:
                parts = [part for part in (left, title, right) if part]
                return " - ".join(parts)

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

        palette = get_theme(theme)
        top = f"{palette['border']}{top}|n"
        bottom = f"{palette['border']}{bottom}|n"
        name_line = f"{palette['border']}│|n{left}{' ' * space}{right}{palette['border']}│|n"
        title_line = f"{palette['border']}│|n{title_content}{palette['border']}│|n"

        return "\n".join((top, name_line, title_line, bottom))


def kv_row(
        k1: str,
        v1: str,
        k2: str | None = None,
        v2: str | None = None,
        *,
        width: int = 60,
        keyw: int = 12,
        theme: Mapping[str, str] | None = None,
        screen_reader: bool = False,
) -> str:
        """Return a pair of key/value fields padded for a consistent layout."""

        col_width = (width - 2) // 2
        palette = get_theme(theme)
        if screen_reader:
                left_key = f"{k1}:".ljust(keyw + 1)
                left = f"{left_key} {apply_screen_reader(v1)}".rstrip()
        else:
                left_key = _ansi_pad(f"{palette['label']}{k1}:|n", keyw + 1)
                left = f"{left_key} {v1}".rstrip()
        if not k2:
                return left

        if screen_reader:
                right_key = f"{k2}:".ljust(keyw + 1)
                right = f"{right_key} {apply_screen_reader(v2)}".rstrip()
        else:
                right_key = _ansi_pad(f"{palette['label']}{k2}:|n", keyw + 1)
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


def chip(text: str, color: str = "|y", *, theme: Mapping[str, str] | None = None,
         screen_reader: bool = False) -> str:
        """Return ``text`` wrapped in a simple colored chip."""

        if screen_reader:
                return f"[{apply_screen_reader(text)}]"
        palette = get_theme(theme)
        border = palette.get("muted", "|w")
        return f"{border}[|n{color}{text}|n{border}]|n"


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


def join_items(
        pairs: Iterable[tuple[str, int]] | Sequence[tuple[str, int]],
        *,
        max_items: int = 5,
        theme: Mapping[str, str] | None = None,
        screen_reader: bool = False,
) -> str:
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
        shown = [
                chip(f"{name} × {count}", "|y", theme=theme, screen_reader=screen_reader)
                for name, count in normalized[:max_items]
        ]
        remaining = len(normalized) - len(shown)
        if remaining > 0:
                shown.append(
                        chip(
                                f"+{remaining} more…",
                                "|x",
                                theme=theme,
                                screen_reader=screen_reader,
                        )
                )
        joined = " ".join(shown)
        return joined if not screen_reader else apply_screen_reader(joined)


def format_currency(value) -> str:
        """Return ``value`` formatted as a Poké-dollar amount."""

        if value is None:
            return "Unknown"
        try:
            amount = int(value)
        except (TypeError, ValueError):
            return str(value)
        sign = "-" if amount < 0 else ""
        return f"{sign}₽ {abs(amount):,}"


def money_line(wallet, bank=None, *, theme: Mapping[str, str] | None = None,
               screen_reader: bool = False) -> str:
        """Return a chip summary for wallet/bank style balances."""

        palette = get_theme(theme)

        def _chip(label: str, amount) -> str:
                formatted = format_currency(amount)
                try:
                        numeric = int(amount)
                except (TypeError, ValueError):
                        numeric = None
                color = palette['ok'] if numeric is None or numeric >= 0 else palette['bad']
                return chip(f"{label} {formatted}", color, theme=palette, screen_reader=screen_reader)

        parts = [_chip("Wallet", wallet)]
        if bank is not None:
                parts.append(_chip("Bank", bank))
        return " ".join(parts)


def status_code(status: str | None, *, theme: Mapping[str, str] | None = None,
                screen_reader: bool = False) -> str:
        """Return a colour-coded three-letter status code."""

        code = (status or "NRM").upper()[:3]
        palette = get_theme(theme)
        lowered = code.lower()
        if lowered in {"brn", "psn"}:
                color = palette['bad']
        elif lowered in {"par", "frz", "slp"}:
                color = palette['warn']
        else:
                color = palette['ok']
        if screen_reader:
                return code
        return f"{color}{code}|n"


TYPE_COLORS: Mapping[str, str] = {
        "normal": "|w",
        "fire": "|r",
        "water": "|B",
        "electric": "|y",
        "grass": "|g",
        "ice": "|C",
        "fighting": "|R",
        "poison": "|m",
        "ground": "|Y",
        "flying": "|c",
        "psychic": "|M",
        "bug": "|G",
        "rock": "|Y",
        "ghost": "|M",
        "dragon": "|b",
        "dark": "|n",
        "steel": "|W",
        "fairy": "|P",
}


def type_chip(type_name: str | None, *, theme: Mapping[str, str] | None = None,
              screen_reader: bool = False) -> str:
        """Return a coloured type label."""

        if not type_name:
                return "Unknown" if screen_reader else f"{get_theme(theme)['muted']}Unknown|n"
        color = TYPE_COLORS.get(str(type_name).lower(), get_theme(theme)['type'])
        if screen_reader:
                return str(type_name)
        return f"{color}{type_name}|n"


def stat_summary_row(
        stats: Mapping[str, int | None],
        *,
        theme: Mapping[str, str] | None = None,
        screen_reader: bool = False,
        width: int = 60,
) -> str:
        """Return a single line stat summary using common stat keys."""

        palette = get_theme(theme)
        order = [
                ("PhysAtk", ("phys_atk", "physical_attack", "attack")),
                ("PhysDef", ("phys_def", "physical_defense", "defense")),
                ("SpecAtk", ("sp_atk", "special_attack", "sp_attack")),
                ("SpecDef", ("sp_def", "special_defense", "sp_defense")),
                ("Speed", ("speed",)),
        ]

        parts: list[str] = []
        for label, keys in order:
                value = None
                for key in keys:
                        if key in stats:
                                value = stats.get(key)
                                break
                display = "—" if value in (None, "") else str(value)
                if screen_reader:
                        parts.append(f"{label}: {display}")
                else:
                        parts.append(f"{palette['label']}{label}|n {palette['value']}{display}|n")

        line = "  ".join(parts)
        if screen_reader:
                return line
        return _ansi_pad(line, width)

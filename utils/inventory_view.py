"""Helpers for rendering trainer inventory tables."""

from __future__ import annotations

from typing import Iterable, List, Tuple

from evennia.utils import ansi as _ansi
from evennia.utils import utils as _utils

ItemPairs = List[Tuple[str, int]]

__all__ = ["gather_inventory_pairs", "format_inventory_table"]


def _strip(text: str) -> str:
        """Return ``text`` without ANSI codes as a plain string."""

        raw = str(text or "")
        if hasattr(_utils, "strip_ansi"):
                return _utils.strip_ansi(raw)
        return _ansi.strip_ansi(raw)


def gather_inventory_pairs(char) -> ItemPairs:
        """Return a normalised list of ``(name, count)`` items for ``char``."""

        pairs: ItemPairs = []

        db = getattr(char, "db", None)
        db_inventory = getattr(db, "inventory", None)

        sources: list[Iterable] = []
        if isinstance(db_inventory, dict):
                sources.append(db_inventory.items())
        elif hasattr(db_inventory, "items"):
                try:
                        sources.append(db_inventory.items())
                except Exception:
                        pass

        if not sources:
                inv_attr = getattr(char, "inventory", None)
                if isinstance(inv_attr, dict):
                        sources.append(inv_attr.items())
                elif inv_attr is not None:
                        sources.append(inv_attr)

        if not sources:
                contents = getattr(char, "contents", None)
                if contents is not None:
                        sources.append(contents)

        for source in sources:
                try:
                        for entry in source:
                                if isinstance(entry, tuple) and len(entry) == 2:
                                        name, count = entry
                                        pairs.append((str(name), int(count)))
                                else:
                                        pairs.append((getattr(entry, "key", str(entry)), 1))
                except Exception:
                        continue

        merged: dict[str, int] = {}
        for name, count in pairs:
                key = _strip(name)
                try:
                        value = max(1, int(count))
                except Exception:
                        value = 1
                merged[key] = merged.get(key, 0) + value

        normalised = [(k, v) for k, v in merged.items()]
        normalised.sort(key=lambda item: (item[0].lower(), item[0]))
        return normalised


def _pad_cell(text: str, width: int) -> str:
        """Return ``text`` padded to ``width`` characters without ANSI codes."""

        visible = len(_strip(text))
        pad = max(0, width - visible)
        return f"{text}{' ' * pad}"


def format_inventory_table(
        pairs: ItemPairs,
        *,
        page: int = 1,
        rows: int = 10,
        cols: int = 3,
        width: int = 60,
) -> tuple[str, str]:
        """Return a tuple of (body, footer) strings for ``pairs`` on ``page``."""

        if page < 1:
                page = 1

        cells = [f"{name} × {count}" for name, count in pairs]
        if not cells:
                return "", "Page 1/1    Items 0 of 0"
        per_page = max(1, rows * cols)
        total_pages = max(1, (len(cells) + per_page - 1) // per_page)
        page = min(page, total_pages)

        start = (page - 1) * per_page
        chunk = cells[start : start + per_page]

        gap = 2
        col_width = max(10, (width - gap * (cols - 1)) // cols)

        lines: List[str] = []
        for row in range(rows):
                parts: List[str] = []
                for col in range(cols):
                        idx = row + col * rows
                        if idx < len(chunk):
                                parts.append(_pad_cell(chunk[idx], col_width))
                        else:
                                parts.append(" " * col_width)
                lines.append((" " * gap).join(parts).rstrip())

        body = "\n".join(lines).rstrip()
        end_index = min(start + len(chunk), len(cells))
        footer = f"Page {page}/{total_pages}    Items {start + 1}-{end_index} of {len(cells)}"
        return body, footer


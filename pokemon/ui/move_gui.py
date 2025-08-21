"""Utilities for rendering move selection GUI with ANSI-safe alignment."""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional

from evennia.utils.ansi import strip_ansi
from pokemon.data.text import MOVES_TEXT

_MOVEDEX: Optional[Dict[str, Any]] = None
# Maximum number of lines allowed for a description; actual rows are
# determined per move-pair so we don't pad with excessive whitespace.
_MAX_DESC_LINES = 4


def _normalize_key(name: str) -> str:
    """Normalize names for case-insensitive lookups."""
    return name.replace(" ", "").replace("-", "").replace("'", "").lower()


def _ensure_movedex() -> Dict[str, Any]:
    """Load move data lazily from the project's movedex."""
    global _MOVEDEX
    if _MOVEDEX is not None:
        return _MOVEDEX
    try:
        from pokemon.dex import MOVEDEX, MOVEDEX_PATH
        from pokemon.dex.entities import load_movedex

        _MOVEDEX = MOVEDEX or load_movedex(MOVEDEX_PATH)
    except Exception:  # pragma: no cover - fall back to direct path
        try:
            from pokemon.dex.entities import load_movedex  # type: ignore

            path = Path(__file__).resolve().parents[1] / "dex" / "movedex.py"
            _MOVEDEX = load_movedex(path)
        except Exception:  # pragma: no cover
            _MOVEDEX = {}
    return _MOVEDEX


# ---------- ANSI-safe helpers ----------


def ansi_len(s: str) -> int:
    """Return the printable length of a string excluding ANSI codes."""
    return len(strip_ansi(s or ""))


def rpad(s: str, width: int, fill: str = " ") -> str:
    """Right-pad ``s`` to the given width accounting for ANSI codes."""
    pad = max(0, width - ansi_len(s))
    return s + (fill * pad)


def center_ansi(s: str, width: int) -> str:
    """Center ``s`` in a field of ``width`` characters ignoring ANSI codes."""
    missing = max(0, width - ansi_len(s))
    left = missing // 2
    right = missing - left
    return (" " * left) + s + (" " * right)


# ---------- Type color (edit to taste) ----------

TYPE_COLOR = {
    "normal": "|w",
    "fire": "|r",
    "water": "|b",
    "grass": "|g",
    "electric": "|y",
    "ice": "|c",
    "fighting": "|r",
    "poison": "|m",
    "ground": "|y",
    "flying": "|c",
    "psychic": "|m",
    "bug": "|g",
    "rock": "|y",
    "ghost": "|m",
    "dragon": "|c",
    "dark": "|x",
    "steel": "|w",
    "fairy": "|m",
}


def tcolor(t: str) -> str:
    """Return color code for a given move type."""
    return TYPE_COLOR.get((t or "").lower(), "|w")


# ---------- Move lookup adaptor ----------


def lookup_move(name: str) -> Optional[Dict[str, Any]]:
    """Fetch move data from the loaded movedex.

    Parameters
    ----------
    name: str
        Name of the move to search for.

    Returns
    -------
    Optional[Dict[str, Any]]
        Dictionary with move details or ``None`` if not found.
    """
    if not name:
        return None
    md = _ensure_movedex()
    mv = md.get(name.lower()) if md else None
    if not mv:
        return None
    entry = MOVES_TEXT.get(_normalize_key(name))
    short_desc = entry.get("shortDesc") if entry else None
    return {
        "name": mv.name,
        "type": mv.type,
        "category": mv.category,
        "pp": mv.pp,
        "accuracy": mv.accuracy,
        "power": mv.power,
        "shortDesc": short_desc,
    }


# ---------- Card builder ----------


def _move_to_model(slot_label: str, move: Any, current_pp: Optional[int] = None) -> Dict[str, Any]:
    """Normalize different move inputs into a common dictionary model."""
    if move is None:
        return {
            "label": slot_label,
            "name": "|wNone|n",
            "type": None,
            "type_disp": "None",
            "cat": "None",
            "pp": (0, 0) if current_pp is None else (current_pp, 0),
            "acc": "—",
            "power": "—",
            "color": "|w",
            "desc": "—",
        }

    if isinstance(move, str):
        data: Dict[str, Any] = lookup_move(move) or {}
    elif isinstance(move, dict):
        data = move
    else:
        # Generic object. Extract common attributes and fall back to lookup
        # in the movedex when details are missing.  This allows passing Django
        # ``Move`` models or other light objects that only define ``name``.
        data = {
            "name": getattr(move, "name", "Unknown"),
            "type": getattr(move, "type", None),
            "category": getattr(move, "category", getattr(move, "cat", None)),
            "pp": getattr(move, "pp", None),
            "accuracy": getattr(move, "accuracy", None),
            "power": getattr(move, "power", getattr(move, "base_power", None)),
            "shortDesc": getattr(move, "shortDesc", None),
        }
        if any(data.get(k) in (None, "") for k in ("type", "category", "pp", "accuracy", "power", "shortDesc")):
            extra = lookup_move(data["name"])
            if extra:
                for key in (
                    "type",
                    "category",
                    "pp",
                    "accuracy",
                    "power",
                    "shortDesc",
                ):
                    if data.get(key) in (None, ""):
                        data[key] = extra.get(key)

    name = data.get("name") or "Unknown"
    key = getattr(move, "key", _normalize_key(name))
    mtype = data.get("type")
    cat = data.get("category") or "Status"
    maxpp = data.get("pp") or 0
    curpp = current_pp if current_pp is not None else maxpp
    acc = data.get("accuracy")
    powr = data.get("power")

    color = tcolor(mtype)
    type_disp = (color + (mtype or "None").title() + "|n") if mtype else "None"
    desc = data.get("shortDesc") or data.get("desc") or "—"

    return {
        "label": slot_label,
        "name": f"|w{name}|n",
        "key": key,
        "type": mtype,
        "type_disp": type_disp,
        "cat": cat.title(),
        "pp": (curpp, maxpp),
        "acc": "—" if acc in (None, True) else str(int(acc)),
        "power": "—" if powr in (None, 0, "0") and cat.lower() == "status" else str(powr or 0),
        "color": color,
        "desc": desc,
    }


def _wrap_desc(desc: str, box_w: int) -> List[str]:
    """Wrap a description to the card width."""
    lines = textwrap.wrap(desc, width=box_w - 4) or [""]
    return lines[:_MAX_DESC_LINES]


def _render_card(card: Dict[str, Any], box_w: int, rows: int) -> List[str]:
    """Render a single move card as a list of lines.

    Parameters
    ----------
    card: Dict[str, Any]
        Normalized move data.
    box_w: int
        Width of the card in characters.
    rows: int
        Number of description lines to render (max 4).
    """
    top = "/" + "-" * (box_w - 2) + "\\"
    lbl = f"[{card['label']} ]" if len(card["label"]) == 1 else f"[{card['label']}]"
    mid = 1 + (box_w - 2 - ansi_len(lbl)) // 2
    top = top[:mid] + lbl + top[mid + ansi_len(lbl) :]

    name_line = rpad(f"|  {card['name']}", box_w)
    type_cat = f"|  {card['color']}{(card['type'] or 'None').title()}|n   {card['cat']}"
    type_line = rpad(type_cat, box_w)
    raw_lines = _wrap_desc(card["desc"], box_w)
    desc_lines = [rpad(f"|  {ln}", box_w) for ln in raw_lines[:rows]]
    while len(desc_lines) < rows:
        desc_lines.append(rpad("|  ", box_w))
    cur, mx = card["pp"]
    pp_line = rpad(f"|  PP: {cur}/{mx}", box_w)
    pa_line = rpad(f"|  Power: {card['power']}   Accuracy: {card['acc']}", box_w)
    bottom = "\\" + "-" * (box_w - 2) + "/"
    return [top, name_line, type_line, *desc_lines, pp_line, pa_line, bottom]


# ---------- Public API ----------


def render_move_gui(slots: List[Any], pp_overrides: Optional[Dict[int, int]] = None, total_width: int = 76) -> str:
    """Render a 2x2 grid of move cards.

    Parameters
    ----------
    slots: list
        List of four move entries (None, names, dicts or objects).
    pp_overrides: dict, optional
        Mapping of slot index to current PP value.
    total_width: int
        Overall width allotted for the grid.
    """
    pp_overrides = pp_overrides or {}
    inner = max(40, total_width)
    gutter = 2
    col_w = (inner - gutter) // 2
    box_w = max(30, col_w)

    labels = ["A", "B", "C", "D"]
    models: List[Dict[str, Any]] = []
    line_counts: List[int] = []
    for i, m in enumerate(slots + [None] * (4 - len(slots))):
        curpp = pp_overrides.get(i)
        model = _move_to_model(labels[i], m, current_pp=curpp)
        models.append(model)
        line_counts.append(len(_wrap_desc(model["desc"], box_w)))

    row1_rows = min(_MAX_DESC_LINES, max(line_counts[0], line_counts[1]))
    row2_rows = min(_MAX_DESC_LINES, max(line_counts[2], line_counts[3]))

    row1_left = _render_card(models[0], box_w, row1_rows)
    row1_right = _render_card(models[1], box_w, row1_rows)
    row2_left = _render_card(models[2], box_w, row2_rows)
    row2_right = _render_card(models[3], box_w, row2_rows)

    lines: List[str] = []
    for L, R in zip(row1_left, row1_right):
        lines.append(rpad(L, box_w) + " " * gutter + rpad(R, box_w))
    for L, R in zip(row2_left, row2_right):
        lines.append(rpad(L, box_w) + " " * gutter + rpad(R, box_w))

    lines.append(
        "Choose a move: A/B/C/D or type the name. Use position for targets (e.g., B1). Type 'cancel' to abort."
    )
    return "\n".join(lines)


__all__ = ["render_move_gui"]

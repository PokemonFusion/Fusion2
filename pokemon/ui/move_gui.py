"""Utilities for rendering move selection GUI with ANSI-safe alignment."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from evennia.utils.ansi import strip_ansi

_MOVEDEX: Optional[Dict[str, Any]] = None


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
    return {
        "name": mv.name,
        "type": mv.type,
        "category": mv.category,
        "pp": mv.pp,
        "accuracy": mv.accuracy,
        "power": mv.power,
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
        }

    if isinstance(move, str):
        data: Dict[str, Any] = lookup_move(move) or {}
    elif isinstance(move, dict):
        data = move
    else:
        data = {
            "name": getattr(move, "name", "Unknown"),
            "type": getattr(move, "type", None),
            "category": getattr(move, "category", getattr(move, "cat", None)),
            "pp": getattr(move, "pp", None),
            "accuracy": getattr(move, "accuracy", None),
            "power": getattr(move, "power", getattr(move, "base_power", None)),
        }

    name = data.get("name") or "Unknown"
    mtype = data.get("type")
    cat = data.get("category") or "Status"
    maxpp = data.get("pp") or 0
    curpp = current_pp if current_pp is not None else maxpp
    acc = data.get("accuracy")
    powr = data.get("power")

    color = tcolor(mtype)
    type_disp = (color + (mtype or "None").title() + "|n") if mtype else "None"

    return {
        "label": slot_label,
        "name": f"|w{name}|n",
        "type": mtype,
        "type_disp": type_disp,
        "cat": cat.title(),
        "pp": (curpp, maxpp),
        "acc": "—" if acc in (None, True) else str(int(acc)),
        "power": "—" if powr in (None, 0, "0") and cat.lower() == "status" else str(powr or 0),
        "color": color,
    }


def _render_card(card: Dict[str, Any], box_w: int) -> List[str]:
    """Render a single move card as a list of lines."""
    top = "/" + "-" * (box_w - 2) + "\\"
    lbl = f"[{card['label']} ]" if len(card['label']) == 1 else f"[{card['label']}]"
    mid = 1 + (box_w - 2 - ansi_len(lbl)) // 2
    top = top[:mid] + lbl + top[mid + ansi_len(lbl):]

    name_line = rpad(f"|  {card['name']}", box_w)
    type_cat = f"|  {card['color']}{(card['type'] or 'None').title()}|n   {card['cat']}"
    type_line = rpad(type_cat, box_w)
    cur, mx = card["pp"]
    pp_line = rpad(f"|  PP: {cur}/{mx}", box_w)
    pa_line = rpad(f"|  Power: {card['power']}   Accuracy: {card['acc']}", box_w)
    bottom = "\\" + "-" * (box_w - 2) + "/"
    return [top, name_line, type_line, pp_line, pa_line, bottom]


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

    cards: List[List[str]] = []
    labels = ["A", "B", "C", "D"]
    for i, m in enumerate(slots + [None] * (4 - len(slots))):
        curpp = pp_overrides.get(i)
        model = _move_to_model(labels[i], m, current_pp=curpp)
        cards.append(_render_card(model, box_w))

    row1_left, row1_right = cards[0], cards[1]
    row2_left, row2_right = cards[2], cards[3]

    lines: List[str] = []
    for L, R in zip(row1_left, row1_right):
        lines.append(rpad(L, box_w) + " " * gutter + rpad(R, box_w))
    for L, R in zip(row2_left, row2_right):
        lines.append(rpad(L, box_w) + " " * gutter + rpad(R, box_w))

    lines.append("Choose a move: A/B/C/D or type the name. Use position for targets (e.g., B1). Type 'cancel' to abort.")
    return "\n".join(lines)


__all__ = ["render_move_gui"]

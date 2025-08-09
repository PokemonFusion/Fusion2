"""Rendering helpers for battle UI elements and move selection boxes."""

from __future__ import annotations
import re
import textwrap

# ─── Configuration ───────────────────────────────────────────
TYPE_COLORS = {
    "Normal":   "|w",  "Fire":     "|r",  "Water":    "|B",
    "Electric": "|y",  "Grass":    "|g",  "Ice":      "|c",
    "Fighting": "|R",  "Poison":   "|m",  "Ground":   "|Y",
    "Flying":   "|C",  "Psychic":  "|M",  "Bug":      "|G",
    "Rock":     "|[",  "Ghost":    "|[143]", "Dragon":   "|[63]",
    "Dark":     "|[240]", "Steel":  "|[246]", "Fairy": "|[218]",
}

CATEGORY_COLORS = {
    "Physical": "|r",
    "Special":  "|B",
    "Status":   "|y",
}

# Matches either |X where X is letter, or |[123] style codes
ANSI_RE = re.compile(r"\|\[[0-9]{1,3}\]|\|[A-Za-z]")

def strip_ansi(s: str) -> str:
    """Remove Evennia-style ANSI codes."""
    return ANSI_RE.sub("", s)

def pad_ansi(s: str, width: int) -> str:
    """
    Pad `s` with spaces up to `width` visible characters,
    ignoring any embedded ANSI sequences.
    """
    visible = len(strip_ansi(s))
    return s + " " * max(0, width - visible)

def fit_visible(text: str, maxw: int) -> str:
    """Truncate `text` to at most `maxw` visible characters."""
    vis = strip_ansi(text)
    if len(vis) <= maxw:
        return text
    short = vis[: max(0, maxw - 1)] + "…"
    return short

def calculate_box_width(moves: dict, min_width: int = 38) -> int:
    """
    Determine the minimum box width needed to fit the longest
    move name, PP, or Power/Accuracy line.
    """
    longest = min_width
    for mv in moves.values():
        if not mv:
            continue
        lines = [
            mv.get("name", "???"),
            f"PP: {mv.get('pp',(0,0))[0]}/{mv.get('pp',(0,0))[1]}",
            f"Power: {mv.get('basePower', mv.get('power', 0))}   Accuracy: {mv.get('accuracy',0)}",
        ]
        for line in lines:
            longest = max(longest, len(strip_ansi(line)) + 4)  # +4 for padding
    return longest

# ─── Rendering ──────────────────────────────────────────────
def dim(s: str) -> str:
    return f"|[244]{s}"

def render_box(label: str, mv: dict, box_width: int) -> list[str]:
    pp_cur, pp_max = mv.get("pp", (0, 0))
    # If out of PP, visually dim name/type/category
    name_vis = mv.get("name", "???")
    mtype     = mv.get("type", "???")
    cat       = mv.get("category", "???")
    if pp_cur == 0 and pp_max > 0:
        name_vis = dim(name_vis)
        mtype    = dim(mtype)
        cat      = dim(cat)
    power = mv.get("basePower", mv.get("power", 0))
    acc   = mv.get("accuracy", 0)

    inner_w = box_width - 4  # subtract borders ("|  " and "  |")

    # 1) top border with centered [label]
    lab = f"[{label}]"
    left  = (box_width - len(lab)) // 2 - 1
    right = box_width - len(lab) - left - 2
    top_line = "/" + "-" * left + lab + "-" * right + "\\"

    # 2) wrap the move name
    wrapped = textwrap.wrap(name_vis, width=inner_w)
    name_lines = [f"|  {line:<{inner_w}}|" for line in wrapped] or [f"|  {'':<{inner_w}}|"]

    # 3) type & category at midpoint
    type_ansi = colorize(mtype, TYPE_COLORS.get(mtype, "|w"))
    cat_ansi  = colorize(cat,   CATEGORY_COLORS.get(cat,   "|w"))
    type_len  = len(strip_ansi(type_ansi))
    cat_len   = len(strip_ansi(cat_ansi))

    mid       = inner_w // 2
    # spaces between type and category so cat starts at 'mid'
    spaces_before = max(0, mid - type_len)
    # spaces after category to fill out full width
    spaces_after  = max(0, inner_w - type_len - spaces_before - cat_len)

    type_field = pad_ansi(type_ansi, type_len)
    cat_field  = pad_ansi(cat_ansi,  cat_len)

    tc_line = (
        "|  "
        + type_field
        + " " * spaces_before
        + cat_field
        + " " * spaces_after
        + "|"
    )

    # 4) PP line
    pp_line = f"|  PP: {pp_cur}/{pp_max:<{inner_w - 7}}|"

    # 5) Power / Accuracy line
    pa_line = f"Power: {power:<3}   Accuracy: {acc:<3}" 
    pa_line = f"|  {pa_line:<{inner_w}}|"

    # 6) bottom border
    bot_line = "\\" + "-" * (box_width - 2) + "/"

    return [top_line] + name_lines + [tc_line, pp_line, pa_line, bot_line]
def render_move_gui(moves: dict) -> str:
    """
    Build a 2x2 ASCII grid of move boxes (A,B on the first row; C,D on the second),
    then append a footer prompt. Uses render_box(...) for each quadrant and
    calculate_box_width(...) to size the boxes. Safely handles missing entries.

    moves: {
      "A": {"name":..., "type":..., "category":..., "pp":(cur,max), "power":..., "accuracy":...},
      "B": {...},
      "C": {...},
      "D": {...},
    }
    """
    # --- local helper: pad a box to a uniform height by inserting blank inner lines
    def _pad_box_to_height(box_lines: list[str], target_h: int, box_width: int) -> list[str]:
        if not box_lines:
            return box_lines
        inner_w = box_width - 4  # accounts for leading "| " and trailing " |"
        blank = f"|  {'':<{inner_w}}|"
        # insert blanks just before the bottom border
        while len(box_lines) < target_h:
            box_lines.insert(-1, blank)
        return box_lines

    # Compute a consistent box width for all four boxes
    box_w = calculate_box_width(moves)

    # Render each quadrant; fall back to empty dict so render_box still returns a frame
    boxes = {
        "A": render_box("A", moves.get("A", {}) or {}, box_w),
        "B": render_box("B", moves.get("B", {}) or {}, box_w),
        "C": render_box("C", moves.get("C", {}) or {}, box_w),
        "D": render_box("D", moves.get("D", {}) or {}, box_w),
    }

    # Normalize heights so side-by-side zip works perfectly
    target_h = max(len(b) for b in boxes.values())
    for k in ("A", "B", "C", "D"):
        boxes[k] = _pad_box_to_height(boxes[k], target_h, box_w)

    # Stitch rows: A|B on first line set, C|D on second
    def _stitch(left: list[str], right: list[str]) -> str:
        return "\n".join(f"{l} {r}" for l, r in zip(left, right))

    grid = _stitch(boxes["A"], boxes["B"]) + "\n" + _stitch(boxes["C"], boxes["D"])

    # Footer prompt — note the target-by-position guidance (A1/B1/etc.)
    prompt = (
        "\n"
        "Choose a move: A/B/C/D or type the name. "
        "Use position for targets (e.g., B1). "
        "Type 'cancel' to abort."
    )

    return grid + prompt


def colorize(text: str, color_code: str) -> str:
    return f"{color_code}{text}|n"


def render_battle_ui(state, viewer, total_width: int = 100) -> str:
    """Proxy to :func:`pokemon.ui.battle_render.render_battle_ui`.

    This wrapper allows callers to import battle UI rendering from this module
    alongside other display helpers without creating circular imports.

    Parameters
    ----------
    state: object
        Battle state providing accessors described by
        :func:`pokemon.ui.battle_render.render_battle_ui`.
    viewer: object
        Trainer or player viewing the interface.
    total_width: int, optional
        Desired total width of the rendered interface.
    """

    from pokemon.ui.battle_render import render_battle_ui as _render

    return _render(state, viewer, total_width=total_width)

# ─── Example usage ─────────────────────────────────────────
if __name__ == "__main__":
    sample = {
        "A": {
            "name": "Tackle",
            "type": "Normal",
            "category": "Physical",
            "pp": (35, 35),
            "basePower": 40,
            "accuracy": 100,
        },
        "B": {
            "name": "Bulldoze",
            "type": "Ground",
            "category": "Physical",
            "pp": (20, 20),
            "basePower": 60,
            "accuracy": 100,
        },
        "C": {
            "name": "Defensecurl",
            "type": "Normal",
            "category": "Status",
            "pp": (40, 40),
            "basePower": 0,
            "accuracy": 1,
        },
        "D": {
            "name": "Mudsport",
            "type": "Ground",
            "category": "Status",
            "pp": (15, 15),
            "basePower": 0,
            "accuracy": 1,
        },
    }
    print(render_move_gui(sample))

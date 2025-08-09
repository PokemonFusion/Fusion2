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

def render_box(label: str, mv: dict, box_width: int) -> list[str]:
    name = mv.get("name", "???")
    mtype = mv.get("type", "???")
    cat   = mv.get("category", "???")
    pp_cur, pp_max = mv.get("pp", (0, 0))
    power = mv.get("basePower", mv.get("power", 0))
    acc   = mv.get("accuracy", 0)

    inner_w = box_width - 4  # subtract borders ("|  " and "  |")

    # 1) top border with centered [label]
    lab = f"[{label}]"
    left  = (box_width - len(lab)) // 2 - 1
    right = box_width - len(lab) - left - 2
    top_line = "/" + "-" * left + lab + "-" * right + "\\"

    # 2) wrap the move name
    wrapped = textwrap.wrap(name, width=inner_w)
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
    Assemble four boxes into a 2×2 grid, labeled A/B on the top row
    and C/D on the bottom, then append the prompt line.
    """
    w = calculate_box_width(moves)
    boxes = {
        k: render_box(k, moves.get(k, {}), w)
        for k in ("A", "B", "C", "D")
    }

    top = "\n".join(a + "  " + b for a, b in zip(boxes["A"], boxes["B"]))
    bot = "\n".join(c + "  " + d for c, d in zip(boxes["C"], boxes["D"]))

    return f"{top}\n{bot}\n|r<Battle>|n Pick an attack, use '|r.abort|n' to cancel:"

def colorize(text: str, color_code: str) -> str:
    return f"{color_code}{text}|n"

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

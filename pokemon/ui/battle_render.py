"""Battle UI renderer: ANSI-safe, width-aware two-column layout with captains/wild title,
HP bars, status badges, party pips, adaptive name/meta row, and a clean footer."""

from utils.battle_display import strip_ansi
from pokemon.ui.box_utils import render_box

# ---------------- Theme ----------------
# Pipe-ANSI color tokens only; callers can later expose a runtime theme toggle.
THEME = {
    "title": "|W",
    "vs": "|Wvs|n",
    "name": "|w",
    "label": "|W",
    "ok": "|g",
    "warn": "|y",
    "bad": "|r",
    "dim": "|n",
    "gender_m": "|C",  # bright cyan
    "gender_f": "|m",  # magenta
    "gender_n": "|x",  # dim/grey
}

# ---------------- ANSI-safe helpers ----------------


def ansi_len(s: str) -> int:
    return len(strip_ansi(s or ""))


def rpad(s: str, width: int, fill: str = " ") -> str:
    pad = max(0, width - ansi_len(s))
    return s + (fill * pad)


def lpad(s: str, width: int, fill: str = " ") -> str:
    pad = max(0, width - ansi_len(s))
    return (fill * pad) + s


def center_ansi(s: str, width: int) -> str:
    missing = max(0, width - ansi_len(s))
    left = missing // 2
    right = missing - left
    return (" " * left) + s + (" " * right)


def ellipsize(text: str, width: int) -> str:
    """Safely shorten raw (non-ANSI) text to ``width`` visible chars with an ellipsis."""
    if width <= 0:
        return ""
    vis = text or ""
    if len(vis) <= width:
        return vis
    if width == 1:
        return "…"
    # reserve one char for ellipsis
    return vis[: width - 1].rstrip() + "…"


# ---------------- Badges / chips ----------------


def status_badge(mon) -> str:
    """Return a short status badge like |yPAR|n or |rBRN|n, or empty."""
    code = getattr(mon, "status", 0)
    # Accept either enum-ish or string-ish statuses
    text = getattr(mon, "status_name", None) or (code if isinstance(code, str) else "")
    text = (text or "").upper()
    if text in ("PAR", "BRN", "PSN", "SLP", "FRZ", "TOX"):
        color = {"PAR": "|y", "BRN": "|r", "PSN": "|m", "SLP": "|c", "FRZ": "|C", "TOX": "|m"}.get(text, "|y")
        return f"{color}{text}|n"
    return ""


def gender_chip(mon) -> str:
    """Return colored gender symbol: ♂, ♀, or – for genderless/unknown."""
    g = getattr(mon, "gender", None)
    if isinstance(g, str):
        g = g.strip().upper()
    if g in ("M", "MALE", "♂"):
        return f"{THEME['gender_m']}♂|n"
    if g in ("F", "FEMALE", "♀"):
        return f"{THEME['gender_f']}♀|n"
    return f"{THEME['gender_n']}–|n"


def display_name(mon) -> str:
    """Return nickname/species composite or fallback name (no ANSI)."""
    nick = (getattr(mon, "nickname", None) or "").strip()
    species = (getattr(mon, "species", None) or getattr(mon, "name", "") or "?").strip()
    if nick and nick.lower() != species.lower():
        return f"{nick} ({species})"
    return species or nick or "?"


def party_pips(trainer, max_team: int = 6) -> str:
    """Return party summary: filled ● for healthy/alive, ◐ for low HP, × for fainted, up to 6."""
    team = list(getattr(trainer, "team", []))[:max_team]
    out = []
    for mon in team:
        if not mon:
            out.append("·")
            continue
        hp, mx = getattr(mon, "hp", 0), getattr(mon, "max_hp", 0)
        if mx <= 0 or hp <= 0:
            out.append("|r×|n")
        else:
            p = 100 * hp // mx if mx else 0
            if p <= 25:
                out.append("|y◐|n")
            else:
                out.append("|g●|n")
    # pad to max_team with faint dots
    while len(out) < max_team:
        out.append("·")
    return " ".join(out)


# ---------------- Bars / numbers ----------------


def hp_bar(cur: int, maxhp: int, width: int = 28) -> str:
    cur = max(0, min(cur, maxhp))
    ratio = 0.0 if maxhp <= 0 else cur / maxhp
    filled = int(width * ratio)
    empty = width - filled
    color = THEME["ok"] if ratio > 0.5 else THEME["warn"] if ratio > 0.2 else THEME["bad"]
    return f"{color}{'█' * filled}{' ' * empty}|n"


def fmt_hp_line(mon, colw: int, show_abs: bool = True) -> str:
    """Return a width-safe HP line that fits inside `colw`.
    Tries right-side text in this order (as space allows):
    - "hp/max (pct%)"  -> requires larger space
    - "hp/max"
    - "pct%"
    If none fit beside a minimally readable bar, shows the bar only."""
    hp = int(getattr(mon, "hp", 0) or 0)
    mx = int(getattr(mon, "max_hp", 0) or 0)
    pct = 0 if mx <= 0 else int(round(100 * hp / mx))

    prefix = f"{THEME['label']}HP|n: "
    sep_two = "  "
    sep_one = " "

    # Build candidate right-hand texts from most to least verbose
    candidates: list[str] = []
    if show_abs:
        candidates.append(f"{hp}/{mx} ({pct}%)")
        candidates.append(f"{hp}/{mx}")
    candidates.append(f"{pct}%")

    def try_fit(sep: str, right: str, min_bar: int) -> str | None:
        avail = colw - ansi_len(prefix) - ansi_len(sep) - ansi_len(right)
        if avail >= min_bar:
            return f"{prefix}{hp_bar(hp, mx, avail)}{sep}{right}"
        return None

    # Prefer a decent-sized bar with two-space separator
    for right in candidates:
        line = try_fit(sep_two, right, min_bar=10)
        if line:
            return line
    # Try again with a single space separator, allow a smaller bar
    for right in candidates:
        line = try_fit(sep_one, right, min_bar=6)
        if line:
            return line
    # Last resort: bar only; ensure at least 3 cells of bar
    bar_only = max(3, colw - ansi_len(prefix))
    return f"{prefix}{hp_bar(hp, mx, bar_only)}"


def _name_and_chips_lines(mon, colw: int) -> list[str]:
    """Adaptive name/meta row(s) with gender, level and status chips."""
    raw_name = display_name(mon)
    name_colored = f"{THEME['name']}{raw_name}|n"
    gchip = gender_chip(mon)
    level = getattr(mon, "level", None)
    lv_chip = f"Lv{level}" if level is not None else ""
    sb = status_badge(mon)
    chips = "  ".join([p for p in (gchip, lv_chip, sb) if p])
    one_line = f"{name_colored}  {chips}" if chips else name_colored
    if ansi_len(one_line) <= colw:
        return [rpad(one_line, colw)]
    # two-line variant
    trunc = raw_name
    if ansi_len(name_colored) > colw:
        trunc = ellipsize(raw_name, colw)
    name_line = rpad(f"{THEME['name']}{trunc}|n", colw)
    chips_line = rpad(chips, colw) if chips else ""
    return [name_line] + ([chips_line] if chips_line else [])


# ---------------- Title helpers ----------------


def _is_wild_battle(me, foe, state) -> bool:
    if getattr(state, "encounter_kind", "").lower() == "wild":
        return True
    if getattr(foe, "is_wild", False):
        return True
    # Heuristic: foe is an NPC shell with a single active Pokémon and no name for a player group
    party = getattr(foe, "team", None)
    is_npc = getattr(foe, "is_npc", False)
    return bool(is_npc and isinstance(party, (list, tuple)) and len(party) <= 1)


def _wild_species(foe) -> str:
    mon = getattr(foe, "active_pokemon", None)
    return getattr(mon, "name", "Wild Pokémon")


def make_title(me, foe, state) -> str:
    player_name = getattr(me, "name", "?")
    if _is_wild_battle(me, foe, state):
        return f"{THEME['title']}{player_name}|n {THEME['vs']} {THEME['title']}Wild {_wild_species(foe)}|n"
    else:
        return f"{THEME['title']}{player_name}|n {THEME['vs']} {THEME['title']}{getattr(foe, 'name', '?')}|n"


# ---------------- Column blocks ----------------


def render_trainer_block(trainer, colw: int, *, show_abs: bool = True) -> list[str]:
    lines: list[str] = []
    mon = getattr(trainer, "active_pokemon", None)
    if mon:
        lines.extend(_name_and_chips_lines(mon, colw))
        lines.append(rpad(fmt_hp_line(mon, colw, show_abs=show_abs), colw))
    else:
        lines.append(rpad("(No active Pokémon)", colw))
    lines.append(rpad(f"{THEME['label']}Team|n: {party_pips(trainer)}", colw))
    return [rpad(line, colw) for line in lines]


# ---------------- Main render ----------------


def render_battle_ui(state, viewer, total_width: int = 78, waiting_on=None) -> str:
    """
    Render the battle UI for `viewer`.
    - Two balanced columns (viewer left).
    - Title shows captains or 'vs Wild <Species>'.
    - Footer: Weather • Field • Turn, plus optional "Waiting on …".
    """
    # layout constants
    gutter = 3

    inner = max(40, total_width - 2)  # inside the outer box
    left_w = (inner - gutter) // 2
    right_w = inner - gutter - left_w

    # sides
    my_side = state.get_side(viewer)
    if my_side == "B":
        left_side, right_side = "B", "A"
    else:
        left_side, right_side = "A", "B"
    me = state.get_trainer(left_side)
    foe = state.get_trainer(right_side)
    show_left = my_side == left_side
    show_right = my_side == right_side

    # ----- Title -----
    title = make_title(me, foe, state)

    # ----- Content -----
    left_lines = render_trainer_block(me, left_w, show_abs=show_left)
    right_lines = render_trainer_block(foe, right_w, show_abs=show_right)

    # equalize height
    max_rows = max(len(left_lines), len(right_lines))
    while len(left_lines) < max_rows:
        left_lines.append(" " * left_w)
    while len(right_lines) < max_rows:
        right_lines.append(" " * right_w)

    rows = []
    for L, R in zip(left_lines, right_lines):
        combined = L + (" " * gutter) + R
        rows.append(rpad(combined, inner))

    # ----- Footer -----
    weather = getattr(state, "weather", getattr(state, "roomweather", "-")) or "-"
    field = getattr(state, "field", "-")
    turn = getattr(state, "round_no", getattr(state, "turn", getattr(state, "round", 0)))
    footer_info = (
        f" {THEME['label']}Weather|n: {weather}   {THEME['label']}Field|n: {field}   {THEME['label']}Turn|n: {turn}"
    )
    footer = rpad(footer_info, inner)

    wait_line = None
    if waiting_on:
        name = getattr(waiting_on, "name", str(waiting_on))
        wait_line = rpad(f" Waiting on {name}...", inner)

    return render_box(title, inner, rows, footer=footer, waiting=wait_line)

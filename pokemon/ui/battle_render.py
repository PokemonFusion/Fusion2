"""Utilities for rendering battle information for trainers.

This module provides helpers for building a two-column battle view that
aligns strings containing ANSI color codes. The left column represents the
viewer and the right column shows the opponent. It also exposes a main
function, :func:`render_battle_ui`, which produces a formatted battle
interface string ready to be sent to a client.
"""

from utils.battle_display import strip_ansi


# ---------- ANSI-safe helpers ----------
def ansi_len(s: str) -> int:
    """Return the length of ``s`` without ANSI color codes."""

    return len(strip_ansi(s or ""))


def rpad(s: str, width: int, fill: str = " ") -> str:
    """Pad ``s`` on the right to ``width`` using ``fill`` characters."""

    pad = max(0, width - ansi_len(s))
    return s + (fill * pad)


def lpad(s: str, width: int, fill: str = " ") -> str:
    """Pad ``s`` on the left to ``width`` using ``fill`` characters."""

    pad = max(0, width - ansi_len(s))
    return (fill * pad) + s


def center_ansi(s: str, width: int) -> str:
    """Center ``s`` within ``width`` characters respecting ANSI codes."""

    missing = max(0, width - ansi_len(s))
    left = missing // 2
    right = missing - left
    return (" " * left) + s + (" " * right)


def hp_bar(cur: int, maxhp: int, width: int = 30) -> str:
    """Return a simple HP bar string.

    Parameters
    ----------
    cur:
        Current HP value.
    maxhp:
        Maximum HP value.
    width:
        Total width of the bar in characters.
    """

    cur = max(0, min(cur, maxhp))
    filled = 0 if maxhp == 0 else int(width * (cur / maxhp))
    return "█" * filled + " " * (width - filled)


def fmt_hp_line(mon, width_bar: int = 30, show_abs: bool = True) -> str:
    """Format a text line showing HP bar and numbers for ``mon``.

    Parameters
    ----------
    mon:
        Pokémon instance with ``hp`` and ``max_hp`` attributes.
    width_bar:
        Width of the HP bar portion.
    show_abs:
        Whether to display absolute HP values in addition to the
        percentage.
    """

    bar = hp_bar(mon.hp, mon.max_hp, width_bar)
    pct = 0 if mon.max_hp == 0 else int(100 * mon.hp / mon.max_hp)
    if show_abs:
        right = f"{mon.hp}/{mon.max_hp} ({pct}%)"
    else:
        right = f"{pct}%"
    return f"|g{bar}|n  {right}"


# ---------- Column renderer ----------
def render_trainer_block(trainer, colw: int, *, show_abs: bool = True) -> list[str]:
    """Return lines for a trainer column without borders.

    Parameters
    ----------
    trainer:
        Trainer object with optional ``active_pokemon`` attribute.
    colw:
        Width of the column in characters.
    show_abs:
        If ``True`` include absolute HP numbers, otherwise show only
        percentages.
    """

    lines: list[str] = []
    mon = getattr(trainer, "active_pokemon", None)
    if mon:
        name_line = f"|w{mon.name}|n Lv{mon.level}"
        lines.append(rpad(name_line, colw))
        hp_line = fmt_hp_line(
            mon, width_bar=max(10, colw - 10), show_abs=show_abs
        )
        lines.append(rpad("HP:", 4) + " " + hp_line)
    else:
        lines.append(rpad("(No active Pokémon)", colw))
    return [rpad(line, colw) for line in lines]


# ---------- Main render ----------
def render_battle_ui(state, viewer, total_width: int = 100, waiting_on=None) -> str:
    """Return a rendered battle UI string for ``viewer``.

    Parameters
    ----------
    state:
        Battle state object providing side and trainer accessors as well as
        weather, field and round information.
    viewer:
        The trainer or player viewing the interface.
    total_width:
        Total desired width of the UI box.
    waiting_on:
        Optional Pokémon instance to indicate a pending action for.
        When supplied, a footer line ``"Waiting on <Pokémon>..."`` is
        appended to the interface.
    """

    # layout constants
    gutter = 3
    border_v = "│"
    border_h = "─"
    corner_l = "┌"
    corner_r = "┐"
    corner_bl = "└"
    corner_br = "┘"
    # columns
    inner = max(40, total_width - 2)  # inside the outer box
    left_w = (inner - gutter) // 2
    right_w = inner - gutter - left_w

    # sides
    my_side = state.get_side(viewer)
    if my_side == "B":
        left_side, right_side = "B", "A"
    else:  # default: viewer on A or spectator
        left_side, right_side = "A", "B"
    me = state.get_trainer(left_side)
    foe = state.get_trainer(right_side)
    show_left = my_side == left_side
    show_right = my_side == right_side

    # BUILD
    title = f"{getattr(me, 'name', '?')} VS {getattr(foe, 'name', '?')}"
    top = (
        corner_l
        + (border_h * ((inner - ansi_len(title)) // 2))
        + " "
        + title
        + " "
        + (border_h * (inner - ((inner - ansi_len(title)) // 2) - ansi_len(title) - 2))
        + corner_r
    )

    # content lines
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
        rows.append(border_v + L + (" " * gutter) + R + border_v)

    footer_info = (
        f" Weather: {getattr(state, 'weather', getattr(state, 'roomweather', '-')) or '-'}"
        f"   Field: {getattr(state, 'field', '-')}"
    )
    bottom = corner_bl + (border_h * max(0, inner - 2)) + corner_br

    # Box with outer vertical borders
    box = [top] + rows + [border_v + rpad(footer_info, inner) + border_v]

    if waiting_on:
        name = getattr(waiting_on, "name", str(waiting_on))
        box.append(border_v + rpad(f" Waiting on {name}...", inner) + border_v)

    box.append(bottom)
    return "\n".join(box)


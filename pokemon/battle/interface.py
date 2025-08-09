"""Battle interface helper functions converted from legacy MUF code."""

from __future__ import annotations

from evennia import search_object
from utils.ansi import ansi

from .state import BattleState


# ---------------------------------------------------------------------------
# Watcher management
# ---------------------------------------------------------------------------

def add_watcher(state: BattleState, watcher) -> None:
    """Register a watcher for battle notifications."""
    if state.watchers is None:
        state.watchers = set()
    state.watchers.add(getattr(watcher, "id", 0))


def remove_watcher(state: BattleState, watcher) -> None:
    """Remove a watcher from the battle."""
    if state.watchers:
        state.watchers.discard(getattr(watcher, "id", 0))


def notify_watchers(state: BattleState, message: str, room=None) -> None:
    """Send `message` to all watchers currently present."""
    if not state.watchers:
        return
    for wid in list(state.watchers):
        objs = search_object(f"#{wid}")
        if not objs:
            continue
        watcher = objs[0]
        if room and watcher.location != room:
            continue
        if watcher.attributes.get("battle_ignore_notify"):
            continue
        watcher.msg(message)


def _party_icons(trainer) -> str:
    """Return party status icons for a trainer."""
    icons = []
    team = getattr(trainer, "team", [])
    for idx in range(6):
        poke = team[idx] if idx < len(team) else None
        if not poke:
            icons.append("-")
            continue
        fainted = getattr(poke, "is_fainted", False) or getattr(poke, "hp", getattr(poke, "current_hp", 0)) <= 0
        status = getattr(poke, "status", "")
        if fainted:
            icons.append("X")
        elif status:
            icons.append("S")
        else:
            icons.append("O")
    return "[" + " ".join(icons) + "]"


def _hp_bar(mon, show_numbers: bool = False, width: int = 40) -> tuple[str, str]:
    hp = getattr(mon, "hp", getattr(mon, "current_hp", 0))
    max_hp = getattr(mon, "max_hp", hp or getattr(mon, "max_hp", 1)) or 1
    ratio = max(0.0, min(1.0, hp / max_hp))
    filled = int(round(ratio * width))
    bar = "█" * filled + "░" * (width - filled)
    if ratio > 0.5:
        bar = ansi.GREEN(bar)
    elif ratio > 0.25:
        bar = ansi.YELLOW(bar)
    else:
        bar = ansi.RED(bar)
    pct = int(round(ratio * 100))
    display = f"{hp}/{max_hp} ({pct}%)" if show_numbers else f"{pct}%"
    return bar, display


def _format_status(status: str) -> str:
    """Return colourised status string."""
    if not status:
        return ""
    code = str(status).upper()
    if code.startswith("PAR"):
        return ansi.YELLOW(code)
    if code.startswith("BRN"):
        return ansi.RED(code)
    if code.startswith("FRZ"):
        return ansi.CYAN(code)
    if code.startswith("SLP"):
        return ansi.BLUE(code)
    if code.startswith("PSN") or code.startswith("TOX"):
        return ansi.MAGENTA(code)
    return code


def _active_info(trainer, *, show_numbers: bool = False) -> list[str]:
    """Return formatted info lines for the trainer's active Pokémon."""

    mon = getattr(trainer, "active_pokemon", None)
    if not mon:
        return ["No active Pokémon."]

    name = getattr(mon, "name", "Unknown")
    level = getattr(mon, "level", "?")
    bar, disp = _hp_bar(mon, show_numbers=show_numbers, width=36)
    status = _format_status(getattr(mon, "status", ""))
    status_part = f" [{status}]" if status else ""
    return [f"{name} Lv{level}", f"HP: {bar} {disp}{status_part}"]


def display_battle_interface(
    trainer,
    opponent,
    battle_state,
    *,
    viewer_team=None,
    waiting_on=None,
) -> str:
    """Return a formatted battle interface string."""
    lines = []
    lines.append(_title_bar(trainer.name, opponent.name))
    t_party = _party_icons(trainer)
    o_party = _party_icons(opponent)
    lines.append(f"║ {t_party:<36}  {o_party:>36} ║")
    lines.append(_legend_line())

    # Active mons (your existing _active_info is reused)
    lines.append("╟" + "─" * 76 + "╢")
    show_a = viewer_team == "A"
    show_b = viewer_team == "B"
    for line in _active_info(trainer, show_numbers=show_a):
        lines.append(line)
    for line in _active_info(opponent, show_numbers=show_b):
        lines.append(line)

    # Meta row (Weather/Field/Round)
    lines.append(_meta_line(
        getattr(battle_state, "weather", getattr(battle_state, "roomweather", "-")),
        getattr(battle_state, "field", "-"),
        getattr(battle_state, "round", getattr(battle_state, "turn", "?")),
    ))


    # Action queue for spectators (from state.declare)
    lines.extend(_action_queue(battle_state))

    # Optional footer (who we’re waiting on)
    if waiting_on:
        lines.append("╟" + "─" * 76 + "╢")
        lines.append(f"║ Waiting on: {waiting_on:<64}║")

    lines.append("╚" + "═" * 76 + "╝")
    return "\n".join(lines)

def _title_bar(left: str, right: str, width: int = 78) -> str:
    center = f" {left} VS {right}"
    pad = max(0, width - len(center))
    left_d = pad // 2
    right_d = pad - left_d
    return "╔" + "═" * left_d + center + "═" * right_d + "╗" 

def _meta_line(weather: str, field: str, rnd) -> str:
    meta = f"Weather: {weather or '-'}   Field: {field or '-'}   Round: {rnd}"
    return f"║ {meta:<76}║"

def _legend_line() -> str:
    return "║ O=OK  S=Status  X=Fainted".ljust(77) + "║"

def _action_queue(battle_state, *, width: int = 78) -> list[str]:
    lines = []
    decl = getattr(battle_state, "declare", {}) or {}
    if not decl:
        return lines
    lines.append("╟" + "─" * (width - 2) + "╢")
    lines.append("║ Declared actions:".ljust(77) + "║")
    # Render sorted by position key so A1, B1, A2, B2…
    for pos in sorted(decl.keys()):
        info = decl[pos]
        if "move" in info:
            s = f"{pos}: {info['move']} → {info.get('target','?')}"
        elif "switch" in info:
            s = f"{pos}: Switch → {info['switch']}"
        elif "item" in info:
            s = f"{pos}: Item → {info['item']}"
        elif "run" in info:
            s = f"{pos}: Attempting to run"
        else:
            s = f"{pos}: …"
        lines.append(f"║   {s:<73}║")
    return lines
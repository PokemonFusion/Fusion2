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
    if not state.watchers:
        state.watchers = {}
    state.watchers[watcher.id] = 1


def remove_watcher(state: BattleState, watcher) -> None:
    """Remove a watcher from the battle."""
    if state.watchers and watcher.id in state.watchers:
        del state.watchers[watcher.id]


def notify_watchers(state: BattleState, message: str, room=None) -> None:
    """Send `message` to all watchers currently present."""
    if not state.watchers:
        return
    for wid in list(state.watchers.keys()):
        objs = search_object(wid)
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


def _hp_bar(mon) -> tuple[str, int]:
    """Return a coloured HP bar and percent."""
    hp = getattr(mon, "hp", getattr(mon, "current_hp", 0))
    max_hp = getattr(mon, "max_hp", hp or getattr(mon, "max_hp", 1)) or 1
    ratio = max(0.0, min(1.0, hp / max_hp))
    filled = int(round(ratio * 40))
    bar = "█" * filled + "░" * (40 - filled)
    if ratio > 0.5:
        bar = ansi.GREEN(bar)
    elif ratio > 0.25:
        bar = ansi.YELLOW(bar)
    else:
        bar = ansi.RED(bar)
    return bar, int(round(ratio * 100))


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


def _active_info(trainer) -> list[str]:
    """Return formatted info lines for the trainer's active Pokémon."""
    mon = getattr(trainer, "active_pokemon", None)
    if not mon:
        return ["No active Pokémon."]
    name = getattr(mon, "name", "Unknown")
    level = getattr(mon, "level", "?")
    bar, pct = _hp_bar(mon)
    status = _format_status(getattr(mon, "status", ""))
    status_part = f" [{status}]" if status else ""
    return [f"{name} Lv{level}", f"HP: {bar} {pct}%{status_part}"]


def display_battle_interface(trainer, opponent, battle_state) -> str:
    """Return a formatted battle interface string."""

    t_party = _party_icons(trainer)
    o_party = _party_icons(opponent)

    lines = []
    header = f"{trainer.name} VS {opponent.name}"
    lines.append(header.center(78))
    lines.append(f"{t_party:<38}{o_party:>38}")
    lines.append("")

    for line in _active_info(trainer):
        lines.append(line)
    for line in _active_info(opponent):
        lines.append(line)

    lines.append("")
    weather = getattr(battle_state, "weather", "-")
    field = getattr(battle_state, "field", "-")
    rnd = getattr(battle_state, "round", getattr(battle_state, "turn", "?"))
    lines.append(f"Weather: {weather}    Field: {field}    Round: {rnd}")

    mon = getattr(trainer, "active_pokemon", None)
    active_name = getattr(mon, "name", "Pokémon") if mon else "Pokémon"
    lines.append("")
    lines.append(f"What will {active_name} do?")
    moves = getattr(mon, "moves", []) if mon else []
    for idx in range(4):
        if idx < len(moves):
            mname = getattr(moves[idx], "name", str(moves[idx]))
        else:
            mname = "-"
        lines.append(f"{idx + 1}) {mname}")

    lines.append("+switch   +item   +flee")
    return "\n".join(lines)

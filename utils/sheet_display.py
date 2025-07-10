"""Utilities for rendering Pokemon sheets."""

from evennia.utils.evtable import EvTable

from utils.ansi import ansi
from commands.command import get_max_hp, get_stats
from utils.xp_utils import get_display_xp, get_next_level_xp
from utils.faction_utils import get_faction_and_rank


__all__ = [
    "display_pokemon_sheet",
    "get_status_effects",
    "format_move_details",
    "get_egg_description",
]


def get_status_effects(pokemon) -> str:
    """Return a short status string for ``pokemon``."""
    status = getattr(pokemon, "status", None)
    return status or "NORM"


def get_egg_description(hatch: int) -> str:
    """Return description text based on hatch progress."""
    # TODO: implement proper egg status checks
    return ""  # placeholder


def format_move_details(move) -> str:
    """Return a formatted move detail line."""
    # TODO: include move class, type, power, accuracy and description
    name = getattr(move, "name", str(move))
    pp = getattr(move, "pp", getattr(move, "current_pp", None))
    max_pp = getattr(move, "max_pp", None)
    if pp is not None and max_pp is not None:
        return f"{name} ({pp}/{max_pp} PP)"
    if pp is not None:
        return f"{name} ({pp} PP)"
    return name


def _hp_bar(current: int, maximum: int, width: int = 20) -> str:
    if maximum <= 0:
        return ""
    ratio = max(0.0, min(1.0, current / maximum))
    filled = int(width * ratio)
    if ratio > 0.5:
        color = ansi.GREEN
    elif ratio > 0.25:
        color = ansi.YELLOW
    else:
        color = ansi.RED
    return color("█" * filled + " " * (width - filled))


def display_pokemon_sheet(caller, pokemon, slot: int | None = None, mode: str = "full") -> str:
    """Return a formatted sheet for ``pokemon``."""
    name = getattr(pokemon, "name", "Unknown")
    species = getattr(pokemon, "species", name)
    gender = getattr(pokemon, "gender", "?")

    level = getattr(pokemon, "level", None)
    if level is None:
        level = get_next_level_xp(pokemon)  # use XP to derive level if needed

    xp = get_display_xp(pokemon)
    next_xp = get_next_level_xp(pokemon)

    hp = getattr(pokemon, "hp", getattr(pokemon, "current_hp", 0))
    max_hp = get_max_hp(pokemon)

    header = name
    if slot is not None:
        header = f"Slot {slot}: {name}"
    lines = [header.center(78)]
    lines.append(f"Species: {species}   Gender: {gender}")
    lines.append(f"Level: {level}   XP: {xp}/{next_xp}")
    lines.append(f"HP: {hp}/{max_hp} {_hp_bar(hp, max_hp)}")
    lines.append(f"Status: {get_status_effects(pokemon)}")
    nature = getattr(pokemon, "nature", "?")
    ability = getattr(pokemon, "ability", "?")
    held = getattr(pokemon, "held_item", "None")
    lines.append(f"Nature: {nature}  Ability: {ability}  Held: {held}")
    # types
    types = getattr(pokemon, "types", getattr(pokemon, "type", []))
    if isinstance(types, (list, tuple)):
        type_str = "/".join(types)
    else:
        type_str = str(types)
    lines.append(f"Type: {type_str}")

    stats = get_stats(pokemon)
    table = EvTable("HP", "Atk", "Def", "SpA", "SpD", "Spe")
    table.add_row(*(str(stats.get(k, "?")) for k in ["hp", "atk", "def", "spa", "spd", "spe"]))
    lines.append(str(table))

    moves = getattr(pokemon, "moves", [])
    lines.append("Moves:")
    for mv in moves:
        lines.append("  " + format_move_details(mv))

    # placeholder features
    lines.append(f"Faction: {get_faction_and_rank(pokemon)}")
    hatch = getattr(pokemon, "hatch", None)
    if getattr(pokemon, "egg", False):
        lines.append(get_egg_description(hatch or 0))

    if mode == "brief":
        # TODO: implement brief display
        pass
    if mode == "moves":
        # TODO: implement move-focused display
        pass

    return "\n".join(lines)

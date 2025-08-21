"""Rendering functions for trainer and Pokémon sheets."""

from evennia.utils.evtable import EvTable
import re
from types import SimpleNamespace

from utils.ansi import ansi
from utils.display_helpers import (
    get_status_effects,
    format_move_details,
    get_egg_description,
)
from pokemon.helpers.pokemon_helpers import get_max_hp, get_stats
from pokemon.models.stats import DISPLAY_STAT_MAP, STAT_KEY_MAP
from utils.xp_utils import get_display_xp, get_next_level_xp
from pokemon.models.stats import level_for_exp
from utils.faction_utils import get_faction_and_rank
from pokemon.dex import POKEDEX, MOVEDEX
from pokemon.utils.pokemon_like import PokemonLike

__all__ = ["display_pokemon_sheet", "display_trainer_sheet"]

# ---- Theme & helpers ---------------------------------------------------------
# Pipe-ANSI friendly theme; override as needed from call-sites later if desired.
THEME = {
    "accent": "|W",
    "muted": "|x",
    "border": "|g",
    "value": "|w",
    "warn": "|y",
    "bad": "|r",
    "good": "|G",
}

# Canonical-ish type colors. Fallback to default if unknown.
TYPE_COLORS = {
    "Normal": "|w",
    "Fire": "|r",
    "Water": "|B",
    "Electric": "|y",
    "Grass": "|g",
    "Ice": "|C",
    "Fighting": "|R",
    "Poison": "|m",
    "Ground": "|Y",
    "Flying": "|c",
    "Psychic": "|M",
    "Bug": "|G",
    "Rock": "|Y",
    "Ghost": "|M",
    "Dragon": "|b",
    "Dark": "|n",
    "Steel": "|W",
    "Fairy": "|P",
}


def _get_pokemon_types(pokemon: PokemonLike) -> list[str]:
    """Return a list of type strings for ``pokemon``."""
    types = getattr(pokemon, "types", None) or getattr(pokemon, "type", None) or getattr(pokemon, "type_", None)
    if types:
        return [types] if isinstance(types, str) else list(types)

    species = getattr(pokemon, "species", None) or getattr(pokemon, "name", None)
    if not species:
        return []

    name = str(species)
    entry = POKEDEX.get(name) or POKEDEX.get(name.capitalize()) or POKEDEX.get(name.lower())
    if entry:
        types = getattr(entry, "types", None)
        if not types and isinstance(entry, dict):
            types = entry.get("types")
        if types:
            return list(types)
    return []


def _color_type(type_name: str) -> str:
    """Return the given type name with color codes."""
    tname = type_name.capitalize()
    prefix = TYPE_COLORS.get(tname, THEME["value"])
    return f"{prefix}{tname}|n"


def _title_bar(text: str, width: int = 78) -> str:
    """Return a centered title bar with ANSI-aware width."""
    border = f"{THEME['border']}-|n"
    title = f"{THEME['accent']}{text}|n"
    side = "-" * max(0, (width - len(text) - 2) // 2)
    return f"{THEME['border']}{side}[|n{title}{THEME['border']}] {side}|n".ljust(width)


def display_trainer_sheet(character) -> str:
    """Return a formatted sheet for a trainer character."""
    name = getattr(character, "key", "Unknown")
    species = character.db.fusion_species or "Human"
    morphology = "Fusion" if character.db.fusion_species else "Human"
    gender = character.db.gender or "?"
    level = character.db.level if character.db.level is not None else "N/A"
    hp = character.db.hp if character.db.hp is not None else "N/A"
    status = character.db.status or "None"

    lines = [name.center(78)]
    lines.append(f"Species: {species}")
    lines.append(f"Morphology: {morphology}   Sex: {gender}")
    lines.append(f"Level: {level}   HP: {hp}")
    lines.append(f"Status: {status}")
    lines.append(f"Faction: {get_faction_and_rank(character)}")

    stats = character.db.stats or {}
    if stats:
        stats_full = {STAT_KEY_MAP.get(k, k): v for k, v in stats.items()}
        headers = [
            DISPLAY_STAT_MAP[s]
            for s in [
                "hp",
                "attack",
                "defense",
                "special_attack",
                "special_defense",
                "speed",
            ]
        ]
        table = EvTable(*headers)
        table.add_row(
            *(
                str(
                    stats_full.get(s, "N/A")
                )
                for s in [
                    "hp",
                    "attack",
                    "defense",
                    "special_attack",
                    "special_defense",
                    "speed",
                ]
            )
        )
        lines.append(str(table))

    return "\n".join(lines)


def _hp_bar(current: int, maximum: int, width: int = 20) -> str:
    """Return a colored HP bar with percentage."""
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
    bar = color("█" * filled + " " * (width - filled))
    pct = int(ratio * 100)
    return f"{bar} {THEME['muted']}({pct}%)|n"


def _maybe_stat_breakdown(pokemon: PokemonLike) -> str | None:
    """Optional IV/EV/nature breakdown if attributes exist on ``pokemon``."""
    ivs = getattr(pokemon, "ivs", None)
    evs = getattr(pokemon, "evs", None)
    if not ivs and not evs:
        return None

    def _row(src, label):
        """Return a formatted row for either dict, sequence or object data."""
        if not src:
            return None
        if hasattr(src, "items"):
            mapping = {STAT_KEY_MAP.get(k, k): v for k, v in src.items()}
        else:
            try:
                seq = list(src)
            except TypeError:
                seq = [
                    getattr(src, "hp", 0),
                    getattr(src, "attack", 0),
                    getattr(src, "defense", 0),
                    getattr(src, "special_attack", 0),
                    getattr(src, "special_defense", 0),
                    getattr(src, "speed", 0),
                ]
            mapping = {
                "hp": seq[0] if len(seq) > 0 else 0,
                "attack": seq[1] if len(seq) > 1 else 0,
                "defense": seq[2] if len(seq) > 2 else 0,
                "special_attack": seq[3] if len(seq) > 3 else 0,
                "special_defense": seq[4] if len(seq) > 4 else 0,
                "speed": seq[5] if len(seq) > 5 else 0,
            }
        return [
            label,
            str(mapping.get("hp", 0)),
            str(mapping.get("attack", 0)),
            str(mapping.get("defense", 0)),
            str(mapping.get("special_attack", 0)),
            str(mapping.get("special_defense", 0)),
            str(mapping.get("speed", 0)),
        ]

    table = EvTable(
        "|w |n",
        "|wHP|n",
        "|wAtk|n",
        "|wDef|n",
        "|wSpA|n",
        "|wSpD|n",
        "|wSpe|n",
        border="table",
    )
    row_iv = _row(ivs, f"{THEME['muted']}IV|n")
    row_ev = _row(evs, f"{THEME['muted']}EV|n")
    if row_iv:
        table.add_row(*row_iv)
    if row_ev:
        table.add_row(*row_ev)
    return str(table)


def display_pokemon_sheet(
    caller, pokemon: PokemonLike, slot: int | None = None, mode: str = "full"
) -> str:
    """Return a formatted sheet for ``pokemon``.

    Parameters
    ----------
    caller : object
        The calling object (unused but kept for API compatibility).
    pokemon : PokemonLike
        The Pokémon to display.
    slot : int or None, optional
        The party slot for labeling.
    mode : str, optional
        One of ``"full"``, ``"brief"`` or ``"moves"``.
    """
    name = getattr(pokemon, "name", "Unknown")
    species = getattr(pokemon, "species", name)
    gender = getattr(pokemon, "gender", "?")

    level = getattr(pokemon, "level", None)
    if level is None:
        xp_val = get_display_xp(pokemon)
        growth = getattr(pokemon, "growth_rate", "medium_fast")
        level = level_for_exp(xp_val, growth)

    xp = get_display_xp(pokemon)
    next_xp = get_next_level_xp(pokemon)

    hp = getattr(pokemon, "hp", getattr(pokemon, "current_hp", 0))
    max_hp = get_max_hp(pokemon)

    header = name if slot is None else f"Slot {slot}: {name}"
    lines = [_title_bar(header)]

    types = _get_pokemon_types(pokemon)
    type_str = " / ".join(_color_type(t) for t in types) if types else f"{THEME['muted']}?|n"
    status_str = get_status_effects(pokemon) or "NORM"
    nature = getattr(pokemon, "nature", None) or "?"
    ability = getattr(pokemon, "ability", None) or "?"
    held = getattr(pokemon, "held_item", None) or "Nothing"

    xp_to = max(0, (next_xp or 0) - (xp or 0))
    xp_pct = 0 if not next_xp else int(min(100, max(0, (xp / next_xp) * 100)))

    top = EvTable(border="none")
    top.add_row(
        f"{THEME['muted']}Species|n: {THEME['value']}{species}|n    "
        f"{THEME['muted']}Gender|n: {THEME['value']}{gender}|n    "
        f"{THEME['muted']}Type|n: {type_str}"
    )
    top.add_row(
        f"{THEME['muted']}Level|n: {THEME['value']}{level}|n    "
        f"{THEME['muted']}XP|n: {THEME['value']}{xp}|n/{next_xp} "
        f"{THEME['muted']}({xp_pct}% to next, {xp_to} xp)|n"
    )
    lines.append(str(top))

    lines.append(
        f"{THEME['muted']}HP|n: {THEME['value']}{hp}|n/{max_hp} {_hp_bar(hp, max_hp)}   "
        f"{THEME['muted']}Status|n: {status_str}"
    )
    lines.append(
        f"{THEME['muted']}Nature|n: {THEME['value']}{nature}|n   "
        f"{THEME['muted']}Ability|n: {THEME['value']}{ability}|n   "
        f"{THEME['muted']}Held|n: {THEME['value']}{held}|n"
    )

    stats = {STAT_KEY_MAP.get(k, k): v for k, v in get_stats(pokemon).items()}
    headers = [
        DISPLAY_STAT_MAP[s]
        for s in [
            "hp",
            "attack",
            "defense",
            "special_attack",
            "special_defense",
            "speed",
        ]
    ]
    table = EvTable(*headers, border="table")
    table.add_row(
        *(
            str(stats.get(s, "?"))
            for s in [
                "hp",
                "attack",
                "defense",
                "special_attack",
                "special_defense",
                "speed",
            ]
        )
    )
    lines.append(str(table))

    iv_ev = _maybe_stat_breakdown(pokemon)
    if iv_ev:
        lines.append(f"{THEME['muted']}IV/EV Breakdown|n")
        lines.append(iv_ev)

    moves_display: list = []
    slots_qs = getattr(pokemon, "activemoveslot_set", None)
    if slots_qs:
        try:
            qs = list(slots_qs.all().order_by("slot"))
        except Exception:
            try:
                qs = list(slots_qs.order_by("slot"))
            except Exception:
                qs = list(slots_qs)
        bonuses = getattr(pokemon, "pp_bonuses", {}) or {}
        for slot_obj in qs[:4]:
            move_obj = getattr(slot_obj, "move", None)
            if not move_obj:
                continue
            mname = getattr(move_obj, "name", str(move_obj))
            cur_pp = getattr(slot_obj, "current_pp", None)
            norm = re.sub(r"[\s'\-]", "", mname.lower())
            dex_entry = MOVEDEX.get(norm)
            base_pp = getattr(dex_entry, "pp", None)
            if base_pp is None and isinstance(dex_entry, dict):
                base_pp = dex_entry.get("pp")
            max_pp = None
            if base_pp is not None:
                max_pp = int(base_pp) + int(bonuses.get(norm, 0))
            if cur_pp is None:
                cur_pp = max_pp
            moves_display.append(
                SimpleNamespace(name=mname, current_pp=cur_pp, max_pp=max_pp)
            )
    else:
        moves_display.extend(getattr(pokemon, "moves", []) or [])

    if mode in ("full", "moves"):
        lines.append(_title_bar("Moves"))
        for mv in moves_display:
            lines.append("  " + format_move_details(mv))

    hatch = getattr(pokemon, "hatch", None)
    if getattr(pokemon, "egg", False):
        lines.append(get_egg_description(hatch or 0))

    if mode == "brief":
        lines = []
        type_brief = "/".join(t[:3].upper() for t in (types or [])) or "?"
        stat_spe = stats.get("speed", "?")
        lines.append(
            f"{THEME['value']}{name}|n "
            f"(Lv {level} {type_brief})  "
            f"HP {hp}/{max_hp}  "
            f"Spe {stat_spe}  "
            f"{THEME['muted']}[{status_str}]|n"
        )
        if moves_display:
            mvnames = [getattr(mv, 'name', str(mv)) for mv in moves_display[:4]]
            lines.append(f"{THEME['muted']}Moves|n: {', '.join(mvnames)}")
        return "\n".join(lines)

    return "\n".join(lines)

"""Rendering functions for trainer and Pokémon sheets."""

from evennia.utils.evtable import EvTable

from utils.ansi import ansi
from helpers.display_helpers import (
    get_status_effects,
    format_move_details,
    get_egg_description,
)
from helpers.pokemon_helpers import get_max_hp, get_stats
from pokemon.stats import DISPLAY_STAT_MAP, STAT_KEY_MAP
from utils.xp_utils import get_display_xp, get_next_level_xp
from pokemon.stats import level_for_exp
from utils.faction_utils import get_faction_and_rank
from pokemon.dex import POKEDEX
from pokemon.utils.pokemon_like import PokemonLike

__all__ = ["display_pokemon_sheet", "display_trainer_sheet"]


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


def display_pokemon_sheet(caller, pokemon: PokemonLike, slot: int | None = None, mode: str = "full") -> str:
    """Return a formatted sheet for ``pokemon``."""
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

    header = name
    if slot is not None:
        header = f"Slot {slot}: {name}"
    lines = [header.center(78)]
    lines.append(f"Species: {species}   Gender: {gender}")
    lines.append(f"Level: {level}   XP: {xp}/{next_xp}")
    lines.append(f"HP: {hp}/{max_hp} {_hp_bar(hp, max_hp)}")
    lines.append(f"Status: {get_status_effects(pokemon)}")
    nature = getattr(pokemon, "nature", None) or "?"
    ability = getattr(pokemon, "ability", None) or "?"
    held = getattr(pokemon, "held_item", None) or "Nothing"
    lines.append(f"Nature: {nature}  Ability: {ability}  Held: {held}")
    # types
    types = _get_pokemon_types(pokemon)
    type_str = "/".join(types) if types else "?"
    lines.append(f"Type: {type_str}")

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
    table = EvTable(*headers)
    table.add_row(
        *(
            str(
                stats.get(s, "?")
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

    moves = getattr(pokemon, "moves", []) or []
    lines.append("Moves:")
    for mv in moves:
        lines.append("  " + format_move_details(mv))

    # placeholder features
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

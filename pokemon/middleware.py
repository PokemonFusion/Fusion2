# fusion2/pokemon/middleware.py

import re
from pokemon.dex import POKEDEX as pokedex, MOVEDEX as movedex
from pokemon.data.learnsets.learnsets import LEARNSETS
from pokemon.data.text import MOVES_TEXT


def _get(obj, key, default=None):
    """Helper to get an attribute or dict entry from ``obj``."""

    if isinstance(obj, dict):
        return obj.get(key, default)
    if hasattr(obj, key):
        return getattr(obj, key)
    raw = getattr(obj, "raw", None)
    if isinstance(raw, dict):
        return raw.get(key, default)
    return default

def get_pokemon_by_number(number):
    """Return pokémon data for the given dex number."""

    for name, details in pokedex.items():
        if _get(details, "num") == number:
            return name, details
    return None, None

def get_pokemon_by_name(name):
    """Return pokémon data by name."""

    key = name.lower()
    if key in pokedex:
        return key, pokedex[key]
    for mon_name, details in pokedex.items():
        alt = _get(details, "name", mon_name).lower()
        if mon_name.lower() == key or alt == key:
            return mon_name, details
    return None, None

def format_gender(details):
    """Return a formatted gender ratio string."""

    gender = _get(details, "gender")
    if gender:
        if gender == "M":
            return "All Males"
        if gender == "F":
            return "All Females"
        if gender == "N":
            return "No Gender"

    ratio = _get(details, "genderRatio")
    if ratio:
        male_ratio = ratio.get("M", 0.5) * 100
        female_ratio = ratio.get("F", 0.5) * 100
    else:
        gr = _get(details, "gender_ratio")
        if gr:
            male_ratio = getattr(gr, "M", 0.5) * 100
            female_ratio = getattr(gr, "F", 0.5) * 100
        else:
            male_ratio = 50
            female_ratio = 50
    return f"Male {male_ratio}%, Female {female_ratio}%"

def format_pokemon_details(name, details):
    """Return a formatted description of a pokémon."""

    number = _get(details, "num", "?")
    display_name = _get(details, "name", name)
    types = _get(details, "types", [])

    msg = f"#{number} - {display_name}\n"
    msg += f"Type: {', '.join(types)}\n"
    msg += f"Gender: {format_gender(details)}\n"

    if isinstance(details, dict):
        stats = details.get("baseStats", {})
        abilities = [a for a in details.get("abilities", {}).values()]
        hp = stats.get("hp", 0)
        atk = stats.get("atk", 0)
        defe = stats.get("def", 0)
        spa = stats.get("spa", 0)
        spd = stats.get("spd", 0)
        spe = stats.get("spe", 0)
    else:
        stats = getattr(details, "base_stats", None)
        abilities = [a.name for a in getattr(details, "abilities", {}).values()]
        hp = getattr(stats, "hp", 0)
        atk = getattr(stats, "atk", 0)
        defe = getattr(stats, "def_", 0)
        spa = getattr(stats, "spa", 0)
        spd = getattr(stats, "spd", 0)
        spe = getattr(stats, "spe", 0)

    msg += (
        f"Base Stats: HP {hp}, ATK {atk}, DEF {defe}, SPA {spa}, SPD {spd}, SPE {spe}\n"
    )

    msg += f"Abilities: {', '.join(abilities)}\n"
    msg += f"Height: {_get(details, 'heightm', '?')} m, Weight: {_get(details, 'weightkg', '?')} kg\n"
    msg += f"Color: {_get(details, 'color', 'Unknown')}\n"

    evos = _get(details, "evos") or []
    if evos:
        msg += f"Evolves To: {', '.join(evos)}\n"

    prevo = _get(details, "prevo")
    if prevo:
        evo_level = _get(details, "evoLevel", _get(details, "evo_level", 'N/A'))
        msg += f"Evolved From: {prevo} (at level {evo_level})\n"

    egg_groups = _get(details, "eggGroups", _get(details, "egg_groups", []))
    msg += f"Egg Groups: {', '.join(egg_groups)}\n"
    return msg


def _normalize_key(name: str) -> str:
    """Normalize names for lookup in MOVEDEX."""
    return name.replace(" ", "").replace("-", "").replace("'", "").lower()


def get_move_by_name(name):
    """Return move data from the movedex by name."""

    key = _normalize_key(name)
    if key in movedex:
        return key, movedex[key]
    for move_name, details in movedex.items():
        alt = _normalize_key(_get(details, "name", move_name))
        if alt == key:
            return move_name, details
    return None, None


def get_move_description(details):
    """Return a long description for a move."""

    name = _get(details, "name")
    if name:
        entry = MOVES_TEXT.get(str(name).lower())
        if entry and entry.get("desc"):
            return entry["desc"]
    return _get(details, "desc", "No description available.")


def format_move_details(name, details):
    """Return a formatted string describing a move."""

    msg = f"{_get(details, 'name', name)}\n"
    msg += "-" * 55 + "\n"
    msg += f"Type: {_get(details, 'type', 'Unknown')}\n"
    msg += f"Class: {_get(details, 'category', 'Unknown')}\n"
    power = _get(details, 'basePower', _get(details, 'power', '--'))
    msg += f"Power: {power}\n"
    msg += f"Accuracy: {_get(details, 'accuracy', '--')}\n"
    msg += f"PP: {_get(details, 'pp', '--')}\n"
    msg += f"Target: {_get(details, 'target', '--')}\n"
    msg += f"Priority: {_get(details, 'priority', 0)}\n"
    msg += f"Desc: {get_move_description(details)}\n"
    msg += "-" * 55
    return msg


CODE_RE = re.compile(r"^(?P<gen>\d+)(?P<type>[A-Z])(?P<data>.*)$")


def _parse_codes(codes):
    """Return a mapping of learn types to their highest generation entry."""

    result = {}
    for code in codes:
        m = CODE_RE.match(code)
        if not m:
            continue
        gen = int(m.group("gen"))
        ltype = m.group("type")
        data = m.group("data")
        entry = result.get(ltype)
        if not entry or gen > entry[0]:
            result[ltype] = (gen, data)
    return result


def build_moveset(learnset):
    """Build a categorized moveset from a raw learnset dictionary."""

    moveset = {
        "level-up": [],
        "machine": [],
        "tutor": [],
        "egg": [],
        "event": [],
        "dream": [],
        "virtual": [],
    }

    for move, codes in learnset.items():
        parsed = _parse_codes(codes)
        for letter, (gen, data) in parsed.items():
            if letter == "L":
                level = int(data or 0)
                moveset["level-up"].append((level, move))
            elif letter == "M":
                moveset["machine"].append(move)
            elif letter == "T":
                moveset["tutor"].append(move)
            elif letter == "E":
                moveset["egg"].append(move)
            elif letter == "S":
                moveset["event"].append(move)
            elif letter == "D":
                moveset["dream"].append(move)
            elif letter == "V":
                moveset["virtual"].append(move)

    moveset["level-up"].sort(key=lambda x: x[0])
    for key in ["machine", "tutor", "egg", "event", "dream", "virtual"]:
        moveset[key].sort()
    return moveset


def get_moveset_by_name(name):
    """Return a moveset for the given Pokémon name."""

    key = name.lower()
    data = LEARNSETS.get(key)
    if not data:
        return None, None
    learnset = data.get("learnset", {})
    return key, build_moveset(learnset)


def format_moveset(name, moveset):
    """Format a moveset dictionary for display."""

    lines = [f"Moveset for {name.title()}", "-" * 55]

    if moveset["level-up"]:
        lines.append("Level-up:")
        for level, move in moveset["level-up"]:
            lines.append(f"  Lv {level}: {move}")
        lines.append("")

    for key, title in [
        ("machine", "Machine"),
        ("tutor", "Tutor"),
        ("egg", "Egg"),
        ("event", "Event"),
        ("dream", "Dream World"),
        ("virtual", "Virtual Console"),
    ]:
        if moveset[key]:
            joined = ", ".join(moveset[key])
            lines.append(f"{title}: {joined}")

    return "\n".join(lines)

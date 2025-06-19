# fusion2/pokemon/middleware.py

import re
from pokemon.dex import POKEDEX as pokedex, MOVEDEX as movedex
from pokemon.data.learnsets.learnsets import LEARNSETS

def get_pokemon_by_number(number):
    for name, details in pokedex.items():
        if details["num"] == number:
            return name, details
    return None, None

def get_pokemon_by_name(name):
    name = name.lower()
    if name in pokedex:
        return name, pokedex[name]
    return None, None

def format_gender(details):
    if "gender" in details:
        gender = details["gender"]
        if gender == "M":
            return "All Males"
        elif gender == "F":
            return "All Females"
        elif gender == "N":
            return "No Gender"
    else:
        if "genderRatio" in details:
            gender_ratio = details["genderRatio"]
            male_ratio = gender_ratio.get("M", 0.5) * 100
            female_ratio = gender_ratio.get("F", 0.5) * 100
        else:
            male_ratio = 50
            female_ratio = 50
        return f"Male {male_ratio}%, Female {female_ratio}%"

def format_pokemon_details(name, details):
    msg = f"#{details['num']} - {details['name']}\n"
    msg += f"Type: {', '.join(details['types'])}\n"
    msg += f"Gender: {format_gender(details)}\n"
    msg += f"Base Stats: HP {details['baseStats']['hp']}, ATK {details['baseStats']['atk']}, DEF {details['baseStats']['def']}, SPA {details['baseStats']['spa']}, SPD {details['baseStats']['spd']}, SPE {details['baseStats']['spe']}\n"
    msg += f"Abilities: {', '.join(details['abilities'].values())}\n"
    msg += f"Height: {details['heightm']} m, Weight: {details['weightkg']} kg\n"
    msg += f"Color: {details['color']}\n"
    if "evos" in details:
        msg += f"Evolves To: {', '.join(details['evos'])}\n"
    if "prevo" in details:
        msg += f"Evolved From: {details['prevo']} (at level {details.get('evoLevel', 'N/A')})\n"
    msg += f"Egg Groups: {', '.join(details['eggGroups'])}\n"
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
        alt = _normalize_key(details.get("name", move_name))
        if alt == key:
            return move_name, details
    return None, None


def get_move_description(details):
    """Placeholder: obtain a long description for a move."""
    # TODO: Pull full move descriptions from dataset or external source
    return details.get("desc") or "No description available."


def format_move_details(name, details):
    """Return a formatted string describing a move."""

    msg = f"{details.get('name', name)}\n"
    msg += "-" * 55 + "\n"
    msg += f"Type: {details.get('type', 'Unknown')}\n"
    msg += f"Class: {details.get('category', 'Unknown')}\n"
    msg += f"Power: {details.get('basePower', '--')}\n"
    msg += f"Accuracy: {details.get('accuracy', '--')}\n"
    msg += f"PP: {details.get('pp', '--')}\n"
    msg += f"Target: {details.get('target', '--')}\n"
    msg += f"Priority: {details.get('priority', 0)}\n"
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

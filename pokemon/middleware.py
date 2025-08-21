# fusion2/pokemon/middleware.py

import re
from pathlib import Path

from pokemon.data.learnsets.learnsets import LEARNSETS
from pokemon.data.text import MOVES_TEXT
from pokemon.dex import MOVEDEX as movedex
from pokemon.dex import POKEDEX as pokedex

# Cache for built movesets keyed by normalized Pokémon name
MOVESET_CACHE = {}


def _ensure_movedex():
    """Load the movedex lazily if it failed during initial import."""
    global movedex
    if movedex:
        return movedex
    try:
        from pokemon.dex import MOVEDEX_PATH
        from pokemon.dex.entities import load_movedex
        movedex = load_movedex(MOVEDEX_PATH)
    except Exception:
        try:  # pragma: no cover - secondary path resolution
            from pokemon.dex.entities import load_movedex  # type: ignore
            path = Path(__file__).resolve().parent / "dex" / "combatdex.py"
            movedex = load_movedex(path)
        except Exception:  # pragma: no cover - final fallback
            movedex = {}
    return movedex


def _normalize_key(name: str) -> str:
    """Normalize names for case-insensitive dex lookups."""

    return name.replace(" ", "").replace("-", "").replace("'", "").lower()


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


# Build lookup indices for faster pokémon retrieval
POKEMON_BY_NUMBER = {}
POKEMON_BY_NAME = {}
for mon_name, details in pokedex.items():
    number = _get(details, "num")
    if number is not None and number not in POKEMON_BY_NUMBER:
        POKEMON_BY_NUMBER[number] = (mon_name, details)
    for alias in {mon_name, _get(details, "name", mon_name)}:
        key = _normalize_key(alias)
        POKEMON_BY_NAME[key] = (mon_name, details)


def get_pokemon_by_number(number):
    """Return pokémon data for the given dex number."""

    return POKEMON_BY_NUMBER.get(number, (None, None))


def get_pokemon_by_name(name):
    """Return pokémon data by name."""

    return POKEMON_BY_NAME.get(_normalize_key(name), (None, None))

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
        atk = getattr(stats, "attack", 0)
        defe = getattr(stats, "defense", 0)
        spa = getattr(stats, "special_attack", 0)
        spd = getattr(stats, "special_defense", 0)
        spe = getattr(stats, "speed", 0)

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


def get_move_by_name(name):
    """Return move data from the movedex by name."""
    md = _ensure_movedex()
    key = _normalize_key(name)
    if key in md:
        return key, md[key]
    for move_name, details in md.items():
        alt = _normalize_key(_get(details, "name", move_name))
        if alt == key:
            return move_name, details
    # Fallback to text dataset if move not present in MOVEDEX
    entry = MOVES_TEXT.get(key)
    if entry:
        return key, entry
    return None, None


def get_move_description(details):
    """Return a long description for the given move."""

    name = _get(details, "name", "")
    key = _normalize_key(name)
    entry = MOVES_TEXT.get(key)
    if entry:
        if "desc" in entry:
            return entry["desc"]
        if "shortDesc" in entry:
            return entry["shortDesc"]
    return _get(details, "desc", _get(details, "shortDesc", "No description available."))


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
    """Return a moveset for the given Pokémon name.

    The moveset is constructed once per species and cached for future
    lookups to avoid repeatedly rebuilding the same data.
    """

    key = name.lower()
    if key in MOVESET_CACHE:
        return key, MOVESET_CACHE[key]

    data = LEARNSETS.get(key)
    if not data:
        return None, None

    learnset = data.get("learnset", {})
    moveset = build_moveset(learnset)
    MOVESET_CACHE[key] = moveset
    return key, moveset


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

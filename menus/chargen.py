"""
Chargen EvMenu nodes for Pokémon Fusion.
Moved out of commands/cmd_chargen.py to centralize menus.
"""

from __future__ import annotations

from typing import Dict

from pokemon.data.generation import NATURES as NATURES_MAP
from pokemon.data.generation import generate_pokemon
from pokemon.data.starters import STARTER_LOOKUP, get_starter_names
from pokemon.dex import POKEDEX
from pokemon.helpers.pokemon_helpers import create_owned_pokemon
from pokemon.models.storage import ensure_boxes
from utils.fusion import record_fusion

# ────── BUILD UNIVERSAL POKEMON LOOKUP ─────────────────────────────────────────

# Map lowercased raw key → key, and lowercased display name → key
POKEMON_KEY_LOOKUP: Dict[str, str] = {}
for key, mon in POKEDEX.items():
    POKEMON_KEY_LOOKUP[key.lower()] = key
    raw = mon.raw or {}
    display_name = raw.get("name", mon.name)
    POKEMON_KEY_LOOKUP[display_name.lower()] = key

# ────── CONSTANTS ──────────────────────────────────────────────────────────────

TYPES = [
    "Bug",
    "Dark",
    "Dragon",
    "Electric",
    "Fighting",
    "Fire",
    "Flying",
    "Ghost",
    "Grass",
    "Ground",
    "Ice",
    "Normal",
    "Poison",
    "Psychic",
    "Rock",
    "Steel",
    "Water",
]
NATURE_NAMES = list(NATURES_MAP.keys())
NATURE_LOOKUP = {n.lower(): n for n in NATURE_NAMES}

# Starter‐specific lookup (name/key → key)
STARTER_NAMES = set(STARTER_LOOKUP.keys())

ABORT_INPUTS = {"abort", ".abort", "q", "quit", "exit"}
ABORT_OPTION = {"key": ("q", "quit", "exit"), "desc": "Abort", "goto": "node_abort"}


# ────── HELPERS ────────────────────────────────────────────────────────────────


def _invalid(caller):
    """Notify caller of invalid input."""
    caller.msg("Invalid entry.\nTry again.")


def format_columns(items, columns=4, indent=2):
    """Return items formatted into evenly spaced columns using spaces."""
    lines = []
    col_width = max((len(str(it)) for it in items), default=0) + 2
    for i in range(0, len(items), columns):
        row = items[i : i + columns]
        padded = [str(it).ljust(col_width) for it in row]
        lines.append(" " * indent + "".join(padded).rstrip())
    return "\n".join(lines)


def _generate_instance(species_key: str, level: int):
    """Return a generated Pokémon instance or ``None`` if invalid."""
    try:
        return generate_pokemon(species_key, level=level)
    except ValueError:
        return None


def _build_owned_pokemon(
    char,
    instance,
    ability: str,
    gender: str,
    nature: str,
    level: int,
):
    """Create an ``OwnedPokemon`` from a generated instance."""
    chosen_gender = gender or instance.gender
    chosen_nature = nature or instance.nature
    return create_owned_pokemon(
        instance.species.name,
        char.trainer,
        level,
        gender=chosen_gender,
        nature=chosen_nature,
        ability=ability or instance.ability,
        ivs=[
            instance.ivs.hp,
            instance.ivs.attack,
            instance.ivs.defense,
            instance.ivs.special_attack,
            instance.ivs.special_defense,
            instance.ivs.speed,
        ],
        evs=[0, 0, 0, 0, 0, 0],
    )


def _add_pokemon_to_storage(char, pokemon) -> None:
    """Place a Pokémon into the caller's active party."""
    storage = ensure_boxes(char.storage)
    storage.add_active_pokemon(pokemon)


def _create_starter(
    char,
    species_key: str,
    ability: str,
    gender: str,
    nature: str,
    level: int = 5,
):
    """Instantiate and store a starter Pokémon for the player."""
    instance = _generate_instance(species_key, level)
    if not instance:
        char.msg("That species does not exist.")
        return None

    pokemon = _build_owned_pokemon(char, instance, ability, gender, nature, level)
    _add_pokemon_to_storage(char, pokemon)
    return pokemon


# ────── MENU NODES ─────────────────────────────────────────────────────────────


def start(caller, raw_string):
    text = (
        "Welcome to Pokemon Fusion 2!\n"
        "A: Play a human trainer with a starter Pokémon.\n"
        "B: Play a Fusion without a starter.\n"
        "______________________________________________________________________________"
    )
    options = (
        {"key": ("A", "a"), "desc": "Human trainer", "goto": ("human_gender", {})},
        {
            "key": ("B", "b"),
            "desc": "Fusion (no starter)",
            "goto": ("fusion_gender", {}),
        },
        ABORT_OPTION,
        {"key": "_default", "goto": "_repeat", "exec": _invalid},
    )
    return text, options


def human_gender(caller, raw_string, **kwargs):
    caller.ndb.chargen = {"type": "human"}
    text = "Choose your gender: (M)ale or (F)emale"
    options = (
        {"key": ("M", "m"), "desc": "Male", "goto": ("human_type", {"gender": "Male"})},
        {
            "key": ("F", "f"),
            "desc": "Female",
            "goto": ("human_type", {"gender": "Female"}),
        },
        ABORT_OPTION,
        {"key": "_default", "goto": "_repeat", "exec": _invalid},
    )
    return text, options


def fusion_gender(caller, raw_string, **kwargs):
    caller.ndb.chargen = {"type": "fusion"}
    text = "Choose your gender: (M)ale or (F)emale"
    options = (
        {
            "key": ("M", "m"),
            "desc": "Male",
            "goto": ("fusion_species", {"gender": "Male"}),
        },
        {
            "key": ("F", "f"),
            "desc": "Female",
            "goto": ("fusion_species", {"gender": "Female"}),
        },
        ABORT_OPTION,
        {"key": "_default", "goto": "_repeat", "exec": _invalid},
    )
    return text, options


def human_type(caller, raw_string, **kwargs):
    # stash gender so we can re-enter with the same kwarg
    gender = kwargs["gender"]
    caller.ndb.chargen["player_gender"] = gender

    text = "Choose your favored Pokémon type:\n" + format_columns(TYPES) + "\n"

    # build all the real type-choices
    opts = [{"key": t.lower(), "desc": t, "goto": ("starter_species", {"type": t})} for t in TYPES]
    # abort stays the same
    opts.append(ABORT_OPTION)
    # on anything else, show our invalid-entry msg *and* go back into human_type
    opts.append(
        {
            "key": "_default",
            "exec": _invalid,
            "goto": ("human_type", {"gender": gender}),
        }
    )

    return text, tuple(opts)


def fusion_species(caller, raw_string, **kwargs):
    caller.ndb.chargen["player_gender"] = kwargs.get("gender")
    text = "Enter the species for your fusion:"
    options = (
        {"key": "_default", "goto": "fusion_ability"},
        ABORT_OPTION,
    )
    return text, options


def fusion_ability(caller, raw_string, **kwargs):
    """Accept either raw key or display name here."""
    entry = raw_string.strip()
    if entry.lower() in ABORT_INPUTS:
        return node_abort(caller)

    # Lookup via our universal mapping
    key = POKEMON_KEY_LOOKUP.get(entry.lower())
    if not key:
        caller.msg("Unknown species.\nTry again.")
        return fusion_species(caller, "")

    mon = POKEDEX[key]
    caller.ndb.chargen.update(
        {
            "species_key": key,
            "species": mon.raw.get("name", mon.name),
        }
    )

    # Gather unique abilities
    raw_abs = mon.raw.get("abilities", {}) or {}
    ab_list = []
    for a in raw_abs.values():
        name = a.name if hasattr(a, "name") else a
        if name not in ab_list:
            ab_list.append(name)

        # Skip to nature selection if only one
        if len(ab_list) <= 1:
            caller.ndb.chargen["ability"] = ab_list[0] if ab_list else ""
            return fusion_nature(caller, "")

        text = "Choose your fusion's ability:\n" + format_columns(ab_list) + "\n"
        base_opts = tuple(
            {
                "key": ab.lower(),
                "desc": ab,
                "goto": ("fusion_nature", {"ability": ab}),
            }
            for ab in ab_list
        )
        options = base_opts + (
            ABORT_OPTION,
            {"key": "_default", "goto": "_repeat", "exec": _invalid},
        )
        return text, options


def fusion_nature(caller, raw_string, **kwargs):
    """Prompt for fusion nature."""
    if kwargs.get("ability"):
        caller.ndb.chargen["ability"] = kwargs["ability"]
    text = "Choose your fusion's nature:\n" + format_columns(NATURE_NAMES, columns=5) + "\n"
    options = (
        ABORT_OPTION,
        {"key": "_default", "goto": "fusion_confirm"},
    )
    return text, options


def starter_species(caller, raw_string, **kwargs):
    caller.ndb.chargen["favored_type"] = kwargs.get("type")

    text = "Enter the species for your starter Pokémon\n(use 'starterlist' or 'pokemonlist' to view valid options):"
    options = [
        {
            "key": ("starterlist", "starters", "pokemonlist"),
            "exec": lambda cb: cb.msg("Starter Pokémon:\n" + ", ".join(get_starter_names())),
            "goto": ("starter_species", {"type": caller.ndb.chargen["favored_type"]}),
        },
        ABORT_OPTION,
        {
            "key": "_default",
            "goto": "starter_ability",
        },
    ]
    return text, tuple(options)


def starter_ability(caller, raw_string, **kwargs):
    entry = raw_string.strip().lower()

    if entry in ABORT_INPUTS:
        return node_abort(caller)

    if entry in ("starterlist", "starters", "pokemonlist"):
        caller.msg("Starter Pokémon:\n" + ", ".join(get_starter_names()))
        return starter_species(caller, "", type=caller.ndb.chargen.get("favored_type"))

    key = STARTER_LOOKUP.get(entry)
    if not key:
        caller.msg("Invalid starter species.\nUse 'starterlist' or 'pokemonlist'.")
        return starter_species(caller, "", type=caller.ndb.chargen.get("favored_type"))

    # Valid species
    caller.ndb.chargen["species_key"] = key
    caller.ndb.chargen["species"] = POKEDEX[key].raw.get("name", key)

    mon = POKEDEX[key]
    abilities = mon.raw.get("abilities", {}) or {}

    numeric_keys = sorted(k for k in abilities if k.isdigit())

    lines = ["Choose one of the following abilities:"]
    for k in numeric_keys:
        lines.append(f"  {int(k) + 1}: {abilities[k]}")
    if "H" in abilities:
        lines.append(f"  H: {abilities['H']}")
    text = "\n".join(lines)

    opts = []
    for k in numeric_keys:
        opts.append(
            {
                "key": str(int(k) + 1),
                "desc": f"{abilities[k]}",
                "exec": lambda cb, k=k: cb.ndb.chargen.__setitem__("ability", abilities[k]),
                "goto": "starter_nature",
            }
        )
    if "H" in abilities:
        opts.append(
            {
                "key": "H",
                "desc": f"{abilities['H']}",
                "exec": lambda cb: cb.ndb.chargen.__setitem__("ability", abilities["H"]),
                "goto": "starter_nature",
            }
        )

    opts.append(ABORT_OPTION)
    opts.append(
        {
            "key": "_default",
            "exec": lambda cb: cb.msg("Invalid choice. Please pick 1, 2… or H."),
            "goto": "_repeat",
        }
    )

    return text, tuple(opts)


def starter_nature(caller, raw_string, **kwargs):
    """Prompt for starter nature."""
    text = "Choose your starter's nature:\n" + format_columns(NATURE_NAMES, columns=5) + "\n"
    options = (
        ABORT_OPTION,
        {"key": "_default", "goto": "starter_gender"},
    )
    return text, options


def starter_gender(caller, raw_string, **kwargs):
    entry = raw_string.strip().lower()
    if entry in ABORT_INPUTS:
        return node_abort(caller)
    nature = NATURE_LOOKUP.get(entry)
    if not nature:
        caller.msg("Invalid nature.\nTry again.")
        return starter_nature(caller, "")
    caller.ndb.chargen["nature"] = nature

    key = caller.ndb.chargen.get("species_key")
    data = POKEDEX[key]
    ratio = getattr(data, "gender_ratio", None)
    gender = getattr(data, "gender", None)

    text = "Choose your starter's gender:"
    options: list[dict] = []

    if gender in ("M", "F", "N"):
        desc = {"M": "Male", "F": "Female", "N": "Genderless"}[gender]
        options.append(
            {
                "key": (gender, gender.lower()),
                "desc": desc,
                "goto": ("starter_confirm", {"gender": gender}),
            }
        )
    else:
        m, f = (ratio.M, ratio.F) if ratio else (0.5, 0.5)
        if m > 0:
            options.append(
                {
                    "key": ("M", "m"),
                    "desc": "Male",
                    "goto": ("starter_confirm", {"gender": "M"}),
                }
            )
        if f > 0:
            options.append(
                {
                    "key": ("F", "f"),
                    "desc": "Female",
                    "goto": ("starter_confirm", {"gender": "F"}),
                }
            )
        if m == 0 and f == 0:
            options.append(
                {
                    "key": ("N", "n"),
                    "desc": "Genderless",
                    "goto": ("starter_confirm", {"gender": "N"}),
                }
            )

    options += [
        ABORT_OPTION,
        {"key": "_default", "goto": "_repeat", "exec": _invalid},
    ]
    return text, tuple(options)


def starter_confirm(caller, raw_string, **kwargs):
    if kwargs.get("ability"):
        caller.ndb.chargen["ability"] = kwargs["ability"]
    if kwargs.get("gender"):
        caller.ndb.chargen["starter_gender"] = kwargs["gender"]

    species = caller.ndb.chargen["species"]
    low = species.lower()
    if low in ABORT_INPUTS:
        return node_abort(caller)
    if low in ("starterlist", "starters", "pokemonlist"):
        caller.msg("Starter Pokémon:\n" + ", ".join(get_starter_names()))
        return starter_species(caller, "", type=caller.ndb.chargen.get("favored_type"))
    if low not in STARTER_NAMES:
        caller.msg("Invalid starter species.\nUse 'starterlist' or 'pokemonlist'.")
        return starter_species(caller, "", type=caller.ndb.chargen.get("favored_type"))

        text = (
            f"You chose {caller.ndb.chargen['species']} "
            f"({caller.ndb.chargen['starter_gender']}) "
            f"with ability {caller.ndb.chargen['ability']} "
            f"and nature {caller.ndb.chargen['nature']} as your starter.\n"
            "Proceed? (Y/N)"
        )
    options = (
        {"key": ("Y", "y"), "desc": "Yes", "goto": "finish_human"},
        {"key": ("N", "n"), "desc": "No", "goto": "starter_species"},
        ABORT_OPTION,
        {"key": "_default", "goto": "_repeat", "exec": _invalid},
    )
    return text, options


def fusion_confirm(caller, raw_string, **kwargs):
    if kwargs.get("ability"):
        caller.ndb.chargen["ability"] = kwargs["ability"]

    entry = raw_string.strip().lower()
    if entry:
        if entry in ABORT_INPUTS:
            return node_abort(caller)
        nature = NATURE_LOOKUP.get(entry)
        if not nature:
            caller.msg("Invalid nature.\nTry again.")
            return fusion_nature(caller, "")
        caller.ndb.chargen["nature"] = nature

    species = caller.ndb.chargen["species"]
    if species.lower() in ABORT_INPUTS:
        return node_abort(caller)

    text = (
        f"You chose to fuse with {species} having ability {caller.ndb.chargen['ability']} "
        f"and nature {caller.ndb.chargen['nature']}.\nProceed? (Y/N)"
    )
    options = (
        {"key": ("Y", "y"), "desc": "Yes", "goto": "finish_fusion"},
        {"key": ("N", "n"), "desc": "No", "goto": "fusion_species"},
        ABORT_OPTION,
        {"key": "_default", "goto": "_repeat", "exec": _invalid},
    )
    return text, options


def finish_human(caller, raw_string):
    data = caller.ndb.chargen or {}
    key = data.get("species_key")
    if not key:
        caller.msg("Error: No starter selected.")
        return None, None

        pk = _create_starter(
            caller,
            key,
            data.get("ability"),
            data.get("starter_gender"),
            data.get("nature"),
        )
    if not pk:
        caller.msg("Starter creation failed. Please try again.")
        return None, None
    caller.db.gender = data.get("player_gender")
    caller.db.favored_type = data.get("favored_type")
    caller.msg(f"You received {pk.name} with ability {pk.ability} and nature {pk.nature} as your starter!")
    caller.msg("Character generation complete.")
    return None, None


def finish_fusion(caller, raw_string):
    data = caller.ndb.chargen or {}
    caller.db.gender = data.get("player_gender")
    caller.db.fusion_species = data.get("species")
    fused = None
    species_key = data.get("species_key")
    trainer = getattr(caller, "trainer", None)
    if species_key and trainer:
        try:
            instance = _generate_instance(species_key, 5)
            if instance:
                fused = _build_owned_pokemon(
                    caller,
                    instance,
                    data.get("ability"),
                    data.get("player_gender"),
                    data.get("nature"),
                    5,
                )
                record_fusion(fused, trainer, fused, permanent=True)
                caller.db.fusion_id = getattr(fused, "unique_id", None)
        except Exception:  # pragma: no cover - defensive
            fused = None
    caller.db.fusion_ability = data.get("ability")
    caller.db.fusion_nature = data.get("nature")
    caller.msg(
        "You are now a fusion with "
        f"{data.get('species')} having ability {data.get('ability')} "
        f"and nature {data.get('nature')}"
        "."
    )
    caller.msg("Character generation complete.")
    return None, None


def node_abort(caller, raw_string=None):
    caller.msg("Character generation aborted.")
    return None, None

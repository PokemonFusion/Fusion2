from __future__ import annotations
from typing import Dict

from evennia import Command
from pokemon.utils.enhanced_evmenu import EnhancedEvMenu

from pokemon.dex import POKEDEX
from pokemon.generation import generate_pokemon
from pokemon.models import Pokemon, StorageBox
from pokemon.starters import get_starter_names, STARTER_LOOKUP
from commands.command import heal_pokemon

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
NATURES = list(generate_pokemon.__globals__["NATURES"].keys())

# Starter‐specific lookup (name/key → key)
STARTER_NAMES = set(STARTER_LOOKUP.keys())

ABORT_INPUTS = {"abort", ".abort", "q", "quit", "exit"}
ABORT_OPTION = {"key": ("q", "quit", "exit"), "desc": "Abort", "goto": "node_abort"}


# ────── HELPERS ────────────────────────────────────────────────────────────────


def _invalid(caller):
    """Notify caller of invalid input."""
    caller.msg("Invalid entry.\nTry again.")


def format_columns(items, columns=4, indent=2):
    """Return items formatted into evenly spaced columns."""
    lines = []
    for i in range(0, len(items), columns):
        row = items[i : i + columns]
        lines.append(" " * indent + "\t".join(str(it) for it in row))
    return "\n".join(lines)


def _ensure_storage(char):
    """Ensure the character has 8 storage boxes."""
    storage = char.storage
    if not storage.boxes.exists():
        for i in range(1, 9):
            StorageBox.objects.create(storage=storage, name=f"Box {i}")
    return storage


def _create_starter(
    char,
    species_key: str,
    ability: str,
    gender: str,
    level: int = 5,
):
    """Instantiate and store a starter Pokémon for the player."""
    try:
        instance = generate_pokemon(species_key, level=level)
    except ValueError:
        char.msg("That species does not exist.")
        return
    chosen_gender = gender or instance.gender
    data = {
        "ivs": {
            "hp": instance.ivs.hp,
            "atk": instance.ivs.atk,
            "def": instance.ivs.def_,
            "spa": instance.ivs.spa,
            "spd": instance.ivs.spd,
            "spe": instance.ivs.spe,
        },
        "evs": {s: 0 for s in ["hp", "atk", "def", "spa", "spd", "spe"]},
        "nature": instance.nature,
        "gender": chosen_gender,
    }
    pokemon = Pokemon.objects.create(
        name=instance.species.name,
        level=instance.level,
        type_=", ".join(instance.species.types),
        ability=ability or instance.ability,
        trainer=char.trainer,
        data=data,
    )
    heal_pokemon(pokemon)
    storage = _ensure_storage(char)
    storage.active_pokemon.add(pokemon)
    return pokemon


# ────── COMMAND CLASS ─────────────────────────────────────────────────────────


class CmdChargen(Command):
    """Interactive character creation."""

    key = "chargen"
    locks = "cmd:all()"

    def func(self):
        if self.caller.db.validated:
            self.caller.msg("You are already validated and cannot run chargen again.")
            return
        EnhancedEvMenu(
            self.caller,
            __name__,
            startnode="start",
            cmd_on_exit=None,
            on_abort=node_abort,
            invalid_message="Invalid entry.\nTry again.",
        )


# ────── MENU NODES ─────────────────────────────────────────────────────────────


def start(caller, raw_string):
    if raw_string:
        _invalid(caller)
        return "start"

    text = (
        "Welcome to Pokemon Fusion!\n"
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
        {"key": "_default", "goto": "start", "exec": _invalid},
    )
    return text, options


def human_gender(caller, raw_string, **kwargs):
    if raw_string and not kwargs:
        _invalid(caller)
        return "human_gender"

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
        {"key": "_default", "goto": "human_gender", "exec": _invalid},
    )
    return text, options


def fusion_gender(caller, raw_string, **kwargs):
    if raw_string and not kwargs:
        _invalid(caller)
        return "fusion_gender"

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
        {"key": "_default", "goto": "fusion_gender", "exec": _invalid},
    )
    return text, options


def human_type(caller, raw_string, **kwargs):
    if raw_string and not kwargs:
        _invalid(caller)
        return "human_type"

    caller.ndb.chargen["gender"] = kwargs["gender"]
    text = "Choose your favored Pokémon type:\n" + format_columns(TYPES) + "\n"
    options = tuple(
        {"key": t.lower(), "desc": t, "goto": ("starter_species", {"type": t})}
        for t in TYPES
    ) + (
        ABORT_OPTION,
        {"key": "_default", "goto": "human_type", "exec": _invalid},
    )
    return text, options


def fusion_species(caller, raw_string, **kwargs):
    if raw_string and not kwargs:
        _invalid(caller)
        return "fusion_species"

    caller.ndb.chargen["gender"] = kwargs.get("gender")
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
        return "fusion_species"

    mon = POKEDEX[key]
    raw = mon.raw or {}
    display_name = raw.get("name", mon.name)

    caller.ndb.chargen["species_key"] = key
    caller.ndb.chargen["species"] = display_name

    # Gather abilities
    abilities = [a.name if hasattr(a, "name") else a for a in mon.abilities.values()]
    abilities = list(dict.fromkeys(abilities))

    # If only one, skip straight to confirm
    if len(abilities) <= 1:
        caller.ndb.chargen["ability"] = abilities[0] if abilities else ""
        return fusion_confirm(caller, "")

    text = "Choose your fusion's ability:\n" + format_columns(abilities) + "\n"
    options = tuple(
        {"key": ab.lower(), "desc": ab, "goto": ("fusion_confirm", {"ability": ab})}
        for ab in abilities
    ) + (
        ABORT_OPTION,
        {"key": "_default", "goto": "fusion_ability", "exec": _invalid},
    )
    return text, options


def starter_species(caller, raw_string, **kwargs):
    if raw_string and not kwargs:
        _invalid(caller)
        return "starter_species"

    caller.ndb.chargen["favored_type"] = kwargs.get("type")
    text = (
        "Enter the species for your starter Pokémon\n"
        "(use 'starterlist' or 'pokemonlist' to view valid options):"
    )
    options = (
        {"key": "_default", "goto": "starter_ability"},
        ABORT_OPTION,
    )
    return text, options


def starter_ability(caller, raw_string, **kwargs):
    entry = raw_string.strip()
    if entry.lower() in ABORT_INPUTS:
        return node_abort(caller)

    # Ability‐selection pass
    if caller.ndb.chargen.get("species"):
        for ab in caller.ndb.chargen.get("ability_options", []):
            if ab.lower() == entry.lower():
                caller.ndb.chargen["ability"] = ab
                return starter_gender(caller, "")
        _invalid(caller)
        return "starter_ability"

    # Species‐selection pass
    lentry = entry.lower()
    if lentry in ("starterlist", "starters", "pokemonlist"):
        caller.msg("Starter Pokémon:\n" + ", ".join(get_starter_names()))
        return "starter_species"
    if lentry not in STARTER_NAMES:
        caller.msg("Invalid starter species.\nUse 'starterlist' or 'pokemonlist'.")
        return "starter_species"

    key = STARTER_LOOKUP[lentry]
    data = POKEDEX[key]
    caller.ndb.chargen["species_key"] = key
    caller.ndb.chargen["species"] = data.name

    abilities = [a.name if hasattr(a, "name") else a for a in data.abilities.values()]
    abilities = list(dict.fromkeys(abilities))
    if len(abilities) <= 1:
        caller.ndb.chargen["ability"] = abilities[0] if abilities else ""
        return starter_gender(caller, "")

    caller.ndb.chargen["ability_options"] = abilities
    text = "Choose your Pokémon's ability:\n" + format_columns(abilities) + "\n"
    options = tuple(
        {"key": ab.lower(), "desc": ab, "goto": ("starter_gender", {"ability": ab})}
        for ab in abilities
    ) + (
        ABORT_OPTION,
        {"key": "_default", "goto": "starter_ability", "exec": _invalid},
    )
    return text, options


def starter_gender(caller, raw_string, **kwargs):
    if raw_string and not kwargs:
        _invalid(caller)
        return "starter_gender"

    if kwargs.get("ability"):
        caller.ndb.chargen["ability"] = kwargs["ability"]

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
        {"key": "_default", "goto": "starter_gender", "exec": _invalid},
    ]
    return text, tuple(options)


def starter_confirm(caller, raw_string, **kwargs):
    if raw_string and not kwargs and caller.ndb.chargen.get("species"):
        _invalid(caller)
        return "starter_confirm"

    if kwargs.get("ability"):
        caller.ndb.chargen["ability"] = kwargs["ability"]
    if kwargs.get("gender"):
        caller.ndb.chargen["gender"] = kwargs["gender"]

    species = caller.ndb.chargen["species"]
    low = species.lower()
    if low in ABORT_INPUTS:
        return node_abort(caller)
    if low in ("starterlist", "starters", "pokemonlist"):
        caller.msg("Starter Pokémon:\n" + ", ".join(get_starter_names()))
        return "starter_species"
    if low not in STARTER_NAMES:
        caller.msg("Invalid starter species.\nUse 'starterlist' or 'pokemonlist'.")
        return "starter_species"

    key = STARTER_LOOKUP[low]
    caller.ndb.chargen["species_key"] = key
    caller.ndb.chargen["species"] = POKEDEX[key].raw.get("name", key)

    text = (
        f"You chose {caller.ndb.chargen['species']} "
        f"({caller.ndb.chargen['gender']}) "
        f"with ability {caller.ndb.chargen['ability']} as your starter.\n"
        "Proceed? (Y/N)"
    )
    options = (
        {"key": ("Y", "y"), "goto": "finish_human"},
        {"key": ("N", "n"), "goto": "starter_species"},
        ABORT_OPTION,
        {"key": "_default", "goto": "starter_confirm", "exec": _invalid},
    )
    return text, options


def fusion_confirm(caller, raw_string, **kwargs):
    if raw_string and not kwargs and caller.ndb.chargen.get("species"):
        _invalid(caller)
        return "fusion_confirm"

    if kwargs.get("ability"):
        caller.ndb.chargen["ability"] = kwargs["ability"]

    species = caller.ndb.chargen["species"]
    if species.lower() in ABORT_INPUTS:
        return node_abort(caller)

    text = (
        f"You chose to fuse with {species} "
        f"having ability {caller.ndb.chargen['ability']}.\n"
        "Proceed? (Y/N)"
    )
    options = (
        {"key": ("Y", "y"), "goto": "finish_fusion"},
        {"key": ("N", "n"), "goto": "fusion_species"},
        ABORT_OPTION,
        {"key": "_default", "goto": "fusion_confirm", "exec": _invalid},
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
        data.get("gender"),
    )
    caller.db.gender = data.get("gender")
    caller.db.favored_type = data.get("favored_type")
    caller.msg(f"You received {pk.name} with ability {pk.ability} as your starter!")
    caller.msg("Character generation complete.")
    return None, None


def finish_fusion(caller, raw_string):
    data = caller.ndb.chargen or {}
    caller.db.gender = data.get("gender")
    caller.db.fusion_species = data.get("species")
    caller.db.fusion_ability = data.get("ability")
    caller.msg(
        f"You are now a fusion with {data.get('species')} "
        f"having ability {data.get('ability')}."
    )
    caller.msg("Character generation complete.")
    return None, None


def node_abort(caller, raw_string=None):
    caller.msg("Character generation aborted.")
    return None, None

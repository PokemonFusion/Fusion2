from __future__ import annotations

from evennia import Command
from evennia.utils.evmenu import EvMenu

from pokemon.dex import POKEDEX
from pokemon.generation import generate_pokemon
from pokemon.models import Pokemon, UserStorage, StorageBox
from pokemon.starters import get_starter_names, STARTER_LOOKUP
from commands.command import heal_pokemon


TYPES = [
    "Bug", "Dark", "Dragon", "Electric", "Fighting", "Fire", "Flying",
    "Ghost", "Grass", "Ground", "Ice", "Normal", "Poison", "Psychic",
    "Rock", "Steel", "Water",
]


NATURES = list(generate_pokemon.__globals__["NATURES"].keys())

# Pre-compute the valid starter species names for quick lookup.
STARTER_NAMES = set(STARTER_LOOKUP.keys())

# recognized inputs to abort chargen
ABORT_INPUTS = {"abort", ".abort"}

# reusable abort option for menu nodes
ABORT_OPTION = {"key": ("abort", ".abort"), "desc": "Abort", "goto": "node_abort"}


def _invalid(caller):
    """Notify caller of invalid input."""
    caller.msg("Invalid entry. Try again.")


def format_columns(items, columns=4, indent=2):
    """Return items formatted into evenly spaced columns."""

    lines = []
    for i in range(0, len(items), columns):
        row = items[i : i + columns]
        lines.append(" " * indent + "\t".join(str(it) for it in row))
    return "\n".join(lines)


def _ensure_storage(char):
    """Return the character's storage, creating it and its boxes if missing."""
    storage = char.storage  # property ensures creation
    if not storage.boxes.exists():
        for i in range(1, 9):
            StorageBox.objects.create(storage=storage, name=f"Box {i}")
    return storage


def _create_starter(
    char, species_key: str, ability: str, gender: str, level: int = 5
):
    """Create the starter Pokemon for the player."""
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
        "evs": {stat: 0 for stat in ["hp", "atk", "def", "spa", "spd", "spe"]},
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


class CmdChargen(Command):
    """Interactive character creation."""

    key = "chargen"
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        if caller.db.validated:
            caller.msg("You are already validated and cannot run chargen again.")
            return
        EvMenu(caller, __name__, startnode="start", cmd_on_exit=None)


def start(caller, raw_string):
    if raw_string:
        _invalid(caller)
    text = (
        "Welcome to Pokemon Fusion!\n"
        "A: Play a human trainer with a starter Pokemon.\n"
        "B: Play a Fusion without a starter.\n"
    )
    options = (
        {"desc": "Human trainer", "goto": ("human_gender", {"char_type": "human"})},
        {"desc": "Fusion", "goto": ("fusion_gender", {"char_type": "fusion"})},
        ABORT_OPTION,
        {"key": "_default", "goto": "start"},
    )
    return text, options


def human_gender(caller, raw_string, **kwargs):
    if raw_string and not kwargs:
        _invalid(caller)
    caller.ndb.chargen = {"type": "human"}
    text = "Choose your gender: (M)ale or (F)emale"
    options = (
        {"key": ("M", "m"), "desc": "Male", "goto": ("human_type", {"gender": "Male"})},
        {"key": ("F", "f"), "desc": "Female", "goto": ("human_type", {"gender": "Female"})},
        ABORT_OPTION,
        {"key": "_default", "goto": "human_gender"},
    )
    return text, options


def fusion_gender(caller, raw_string, **kwargs):
    if raw_string and not kwargs:
        _invalid(caller)
    caller.ndb.chargen = {"type": "fusion"}
    text = "Choose your gender: (M)ale or (F)emale"
    options = (
        {"key": ("M", "m"), "desc": "Male", "goto": ("fusion_species", {"gender": "Male"})},
        {"key": ("F", "f"), "desc": "Female", "goto": ("fusion_species", {"gender": "Female"})},
        ABORT_OPTION,
        {"key": "_default", "goto": "fusion_gender"},
    )
    return text, options


def human_type(caller, raw_string, **kwargs):
    if raw_string and not kwargs:
        _invalid(caller)
    caller.ndb.chargen["gender"] = kwargs.get("gender")
    text = "Choose your favored Pokemon type:\n"
    text += format_columns(TYPES) + "\n"
    options = tuple({"key": t.lower(), "desc": t, "goto": ("starter_species", {"type": t})} for t in TYPES)
    options += (ABORT_OPTION, {"key": "_default", "goto": "human_type"})
    return text, options


def fusion_species(caller, raw_string, **kwargs):
    caller.ndb.chargen["gender"] = kwargs.get("gender")
    text = "Enter the species for your fusion:"
    return text, ({"key": "_default", "goto": "fusion_ability"}, ABORT_OPTION)


def fusion_ability(caller, raw_string, **kwargs):
    species = raw_string.strip()
    if species.lower() in ABORT_INPUTS:
        return node_abort(caller)
    if not (species.title() in POKEDEX or species.lower() in POKEDEX):
        caller.msg("Unknown species. Try again.")
        return "fusion_species", {}
    caller.ndb.chargen["species"] = species
    data = POKEDEX.get(species.title()) or POKEDEX.get(species.lower())
    abilities = [
        a.name if hasattr(a, "name") else a for a in data.abilities.values()
    ]
    abilities = list(dict.fromkeys(abilities))
    if len(abilities) <= 1:
        caller.ndb.chargen["ability"] = abilities[0] if abilities else ""
        return fusion_confirm(caller, "")
    text = "Choose your fusion's ability:\n"
    text += format_columns(abilities) + "\n"
    options = tuple({"key": ab.lower(), "desc": ab, "goto": ("fusion_confirm", {"ability": ab})} for ab in abilities)
    options += (ABORT_OPTION, {"key": "_default", "goto": "fusion_ability"})
    return text, options


def starter_species(caller, raw_string, **kwargs):
    if raw_string and not kwargs:
        _invalid(caller)
    caller.ndb.chargen["favored_type"] = kwargs.get("type")
    text = (
        "Enter the species for your starter Pokemon "
        "(use 'starterlist' to view valid options):"
    )
    return text, ({"key": "_default", "goto": "starter_ability"}, ABORT_OPTION)


def starter_ability(caller, raw_string, **kwargs):
    """Handle starter species and ability selection."""
    entry = raw_string.strip()
    if entry.lower() in ABORT_INPUTS:
        return node_abort(caller)

    # If species already chosen we're expecting an ability
    if caller.ndb.chargen.get("species"):
        ability_l = entry.lower()
        ability_opts = caller.ndb.chargen.get("ability_options", [])
        for ab in ability_opts:
            if ab.lower() == ability_l:
                caller.ndb.chargen["ability"] = ab
                caller.ndb.chargen.pop("ability_options", None)
                return starter_gender(caller, "")
        if entry:
            _invalid(caller)
        return "starter_ability", {}

    # Expecting species input
    species_l = entry.lower()
    if species_l in ("starterlist", "starters"):
        caller.msg("Starter Pokémon:\n" + ", ".join(get_starter_names()))
        return "starter_species", {}
    if species_l not in STARTER_NAMES:
        if entry:
            caller.msg("Invalid starter species. Use 'starterlist' for options.")
        return "starter_species", {}

    key = STARTER_LOOKUP[species_l]
    data = POKEDEX.get(key)
    caller.ndb.chargen["species_key"] = key
    caller.ndb.chargen["species"] = data.name
    abilities = [a.name if hasattr(a, "name") else a for a in data.abilities.values()]
    abilities = list(dict.fromkeys(abilities))
    if len(abilities) <= 1:
        caller.ndb.chargen["ability"] = abilities[0] if abilities else ""
        return starter_gender(caller, "")

    caller.ndb.chargen["ability_options"] = abilities
    text = "Choose your pokemon's ability:\n" + format_columns(abilities) + "\n"
    options = tuple({"key": ab.lower(), "desc": ab, "goto": ("starter_gender", {"ability": ab})} for ab in abilities)
    options += (ABORT_OPTION, {"key": "_default", "goto": "starter_ability"})
    return text, options


def starter_gender(caller, raw_string, **kwargs):
    if raw_string and not kwargs:
        _invalid(caller)
    ability = kwargs.get("ability")
    if ability:
        caller.ndb.chargen["ability"] = ability

    species = caller.ndb.chargen.get("species")
    if not species:
        caller.msg("Error: Species not chosen.")
        return "starter_species", {}

    key = caller.ndb.chargen.get("species_key")
    data = POKEDEX.get(key)
    ratio = getattr(data, "gender_ratio", None)
    gender = getattr(data, "gender", None)

    options = []
    text = "Choose your starter's gender:"
    if gender:
        if gender == "N":
            options.append({"key": ("N", "n"), "desc": "Genderless", "goto": ("starter_confirm", {"gender": "N"})})
        elif gender == "M":
            options.append({"key": ("M", "m"), "desc": "Male", "goto": ("starter_confirm", {"gender": "M"})})
        elif gender == "F":
            options.append({"key": ("F", "f"), "desc": "Female", "goto": ("starter_confirm", {"gender": "F"})})
    else:
        if not ratio:
            ratio_m = 0.5
            ratio_f = 0.5
        else:
            ratio_m = ratio.M
            ratio_f = ratio.F
        if ratio_m == 0 and ratio_f == 0:
            options.append({"key": ("N", "n"), "desc": "Genderless", "goto": ("starter_confirm", {"gender": "N"})})
        elif ratio_m == 1:
            options.append({"key": ("M", "m"), "desc": "Male", "goto": ("starter_confirm", {"gender": "M"})})
        elif ratio_f == 1:
            options.append({"key": ("F", "f"), "desc": "Female", "goto": ("starter_confirm", {"gender": "F"})})
        else:
            options.append({"key": ("M", "m"), "desc": "Male", "goto": ("starter_confirm", {"gender": "M"})})
            options.append({"key": ("F", "f"), "desc": "Female", "goto": ("starter_confirm", {"gender": "F"})})

    options.append(ABORT_OPTION)
    options.append({"key": "_default", "goto": "starter_gender"})
    return text, tuple(options)


def starter_confirm(caller, raw_string, **kwargs):
    if raw_string and caller.ndb.chargen.get("species") and not kwargs:
        _invalid(caller)
    ability = kwargs.get("ability")
    if ability:
        caller.ndb.chargen["ability"] = ability
    gender = kwargs.get("gender")
    if gender:
        caller.ndb.chargen["gender"] = gender
    species = caller.ndb.chargen.get("species")
    if not species:
        species = raw_string.strip()
        if species.lower() in ABORT_INPUTS:
            return node_abort(caller)
        species_l = species.lower()
        if species_l in ("starterlist", "starters"):
            caller.msg("Starter Pokémon:\n" + ", ".join(get_starter_names()))
            return "starter_species", {}
        if species_l not in STARTER_NAMES:
            caller.msg("Invalid starter species. Use 'starterlist' for options.")
            return "starter_species", {}
        key = STARTER_LOOKUP[species_l]
        caller.ndb.chargen["species_key"] = key
        caller.ndb.chargen["species"] = POKEDEX[key].name
        species = caller.ndb.chargen["species"]
    text = (
        f"You chose {species.title()}"
        f" ({caller.ndb.chargen.get('gender', '?')})"
        f" with ability {caller.ndb.chargen.get('ability')} as your starter. Proceed? (y/n)"
    )
    options = (
        {"key": ("y", "Y"), "goto": "finish_human"},
        {"key": ("n", "N"), "goto": "starter_species"},
        ABORT_OPTION,
        {"key": "_default", "goto": "starter_confirm"},
    )
    return text, options


def fusion_confirm(caller, raw_string, **kwargs):
    if raw_string and caller.ndb.chargen.get("species") and not kwargs:
        _invalid(caller)
    ability = kwargs.get("ability")
    if ability:
        caller.ndb.chargen["ability"] = ability
    species = caller.ndb.chargen.get("species")
    if not species:
        species = raw_string.strip()
        if species.lower() in ABORT_INPUTS:
            return node_abort(caller)
        if not (species.title() in POKEDEX or species.lower() in POKEDEX):
            caller.msg("Unknown species. Try again.")
            return "fusion_species", {}
        caller.ndb.chargen["species"] = species
    text = (
        f"You chose to fuse with {species.title()} having ability {caller.ndb.chargen.get('ability')}. Proceed? (y/n)"
    )
    options = (
        {"key": ("y", "Y"), "goto": "finish_fusion"},
        {"key": ("n", "N"), "goto": "fusion_species"},
        ABORT_OPTION,
        {"key": "_default", "goto": "fusion_confirm"},
    )
    return text, options


def finish_human(caller, raw_string):
    data = caller.ndb.chargen or {}
    species = data.get("species")
    if not species:
        caller.msg("Error: No species chosen.")
        return None, None
    _create_starter(caller, data.get("species_key"), data.get("ability"), data.get("gender"))
    caller.db.gender = data.get("gender")
    caller.db.favored_type = data.get("favored_type")
    caller.msg(
        f"You received {species.title()} with ability {data.get('ability')} as your starter!"
    )
    caller.msg("Character generation complete.")
    return None, None


def finish_fusion(caller, raw_string):
    data = caller.ndb.chargen or {}
    caller.db.gender = data.get("gender")
    caller.db.fusion_species = data.get("species")
    caller.db.fusion_ability = data.get("ability")
    caller.msg(
        f"You are a fusion with {data.get('species').title()} having ability {data.get('ability')}."
    )
    caller.msg("Character generation complete.")
    return None, None


def node_abort(caller, raw_input=None):
    """Abort character generation."""
    caller.msg("Character generation aborted.")
    return None, None


from __future__ import annotations

from evennia import Command
from evennia.utils.evmenu import EvMenu

from pokemon.dex import POKEDEX
from pokemon.generation import generate_pokemon
from pokemon.models import Pokemon, UserStorage, StorageBox
from pokemon.starters import get_starter_names


TYPES = [
    "Bug", "Dark", "Dragon", "Electric", "Fighting", "Fire", "Flying",
    "Ghost", "Grass", "Ground", "Ice", "Normal", "Poison", "Psychic",
    "Rock", "Steel", "Water",
]


NATURES = list(generate_pokemon.__globals__["NATURES"].keys())

# Pre-compute the valid starter species names for quick lookup.
STARTER_NAMES = set(name.lower() for name in get_starter_names())


def _ensure_storage(char):
    storage, _ = UserStorage.objects.get_or_create(user=char)
    char.storage = storage
    if not storage.boxes.exists():
        for i in range(1, 9):
            StorageBox.objects.create(storage=storage, name=f"Box {i}")
    return storage


def _create_starter(char, species_name: str, ability: str, level: int = 5):
    species = POKEDEX.get(species_name.lower())
    if not species:
        char.msg("That species does not exist.")
        return
    instance = generate_pokemon(species.name, level=level)
    pokemon = Pokemon.objects.create(
        name=instance.species.name,
        level=instance.level,
        type_=", ".join(instance.species.types),
        ability=ability or instance.ability,
    )
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
    text = (
        "Welcome to Pokemon Fusion!\n"
        "A: Play a human trainer with a starter Pokemon.\n"
        "B: Play a Fusion without a starter.\n"
    )
    options = (
        {"desc": "Human trainer", "goto": ("human_gender", {"char_type": "human"})},
        {"desc": "Fusion", "goto": ("fusion_gender", {"char_type": "fusion"})},
    )
    return text, options


def human_gender(caller, raw_string, **kwargs):
    caller.ndb.chargen = {"type": "human"}
    text = "Choose your gender: (M)ale or (F)emale"
    options = (
        {"key": ("M", "m"), "desc": "Male", "goto": ("human_type", {"gender": "Male"})},
        {"key": ("F", "f"), "desc": "Female", "goto": ("human_type", {"gender": "Female"})},
    )
    return text, options


def fusion_gender(caller, raw_string, **kwargs):
    caller.ndb.chargen = {"type": "fusion"}
    text = "Choose your gender: (M)ale or (F)emale"
    options = (
        {"key": ("M", "m"), "desc": "Male", "goto": ("fusion_species", {"gender": "Male"})},
        {"key": ("F", "f"), "desc": "Female", "goto": ("fusion_species", {"gender": "Female"})},
    )
    return text, options


def human_type(caller, raw_string, **kwargs):
    caller.ndb.chargen["gender"] = kwargs.get("gender")
    text = "Choose your favored Pokemon type:\n"
    for t in TYPES:
        text += f"  {t}\n"
    options = tuple({"key": t.lower(), "desc": t, "goto": ("starter_species", {"type": t})} for t in TYPES)
    return text, options


def fusion_species(caller, raw_string, **kwargs):
    caller.ndb.chargen["gender"] = kwargs.get("gender")
    text = "Enter the species for your fusion:"
    return text, ({"key": "*", "goto": "fusion_ability"},)


def fusion_ability(caller, raw_string, **kwargs):
    species = raw_string.strip()
    if species.lower() not in POKEDEX:
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
        return "fusion_confirm", {}
    text = "Choose your fusion's ability:\n"
    for ab in abilities:
        text += f"  {ab}\n"
    options = tuple({"key": ab.lower(), "desc": ab, "goto": ("fusion_confirm", {"ability": ab})} for ab in abilities)
    return text, options


def starter_species(caller, raw_string, **kwargs):
    caller.ndb.chargen["favored_type"] = kwargs.get("type")
    text = (
        "Enter the species for your starter Pokemon "
        "(use 'starterlist' to view valid options):"
    )
    return text, ({"key": "*", "goto": "starter_ability"},)


def starter_ability(caller, raw_string, **kwargs):
    species = raw_string.strip()
    species_l = species.lower()
    if species_l not in STARTER_NAMES:
        caller.msg("Invalid starter species. Use 'starterlist' for options.")
        return "starter_species", {}
    if species_l not in POKEDEX:
        caller.msg("Unknown species. Try again.")
        return "starter_species", {}
    caller.ndb.chargen["species"] = species
    data = POKEDEX.get(species.title()) or POKEDEX.get(species.lower())
    abilities = [
        a.name if hasattr(a, "name") else a for a in data.abilities.values()
    ]
    abilities = list(dict.fromkeys(abilities))
    if len(abilities) <= 1:
        caller.ndb.chargen["ability"] = abilities[0] if abilities else ""
        return "starter_confirm", {}
    text = "Choose your pokemon's ability:\n"
    for ab in abilities:
        text += f"  {ab}\n"
    options = tuple({"key": ab.lower(), "desc": ab, "goto": ("starter_confirm", {"ability": ab})} for ab in abilities)
    return text, options


def starter_confirm(caller, raw_string, **kwargs):
    ability = kwargs.get("ability")
    if ability:
        caller.ndb.chargen["ability"] = ability
    species = caller.ndb.chargen.get("species")
    if not species:
        species = raw_string.strip()
        species_l = species.lower()
        if species_l not in STARTER_NAMES:
            caller.msg("Invalid starter species. Use 'starterlist' for options.")
            return "starter_species", {}
        if species_l not in POKEDEX:
            caller.msg("Unknown species. Try again.")
            return "starter_species", {}
        caller.ndb.chargen["species"] = species
    text = f"You chose {species.title()} with ability {caller.ndb.chargen.get('ability')} as your starter. Proceed? (y/n)"
    options = (
        {"key": ("y", "Y"), "goto": "finish_human"},
        {"key": ("n", "N"), "goto": "starter_species"},
    )
    return text, options


def fusion_confirm(caller, raw_string, **kwargs):
    ability = kwargs.get("ability")
    if ability:
        caller.ndb.chargen["ability"] = ability
    species = caller.ndb.chargen.get("species")
    if not species:
        species = raw_string.strip()
        if species.lower() not in POKEDEX:
            caller.msg("Unknown species. Try again.")
            return "fusion_species", {}
        caller.ndb.chargen["species"] = species
    text = (
        f"You chose to fuse with {species.title()} having ability {caller.ndb.chargen.get('ability')}. Proceed? (y/n)"
    )
    options = (
        {"key": ("y", "Y"), "goto": "finish_fusion"},
        {"key": ("n", "N"), "goto": "fusion_species"},
    )
    return text, options


def finish_human(caller, raw_string):
    data = caller.ndb.chargen or {}
    species = data.get("species")
    if not species:
        caller.msg("Error: No species chosen.")
        return None, None
    _create_starter(caller, species, data.get("ability"))
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


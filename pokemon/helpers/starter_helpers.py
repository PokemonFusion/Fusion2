"""Helpers for chargen starter validation and creation."""

from pokemon.data.generation import generate_pokemon
from pokemon.data.starters import is_valid_starter_key, resolve_starter_key
from pokemon.helpers.pokemon_helpers import create_owned_pokemon
from pokemon.models.storage import ensure_boxes


def create_chargen_starter(
    char,
    species_key: str,
    ability: str,
    gender: str,
    nature: str,
    level: int = 5,
):
    """Create and place a validated chargen starter in the active party."""
    key = resolve_starter_key(species_key) or species_key
    if not is_valid_starter_key(key):
        raise ValueError("Invalid starter species.")

    instance = generate_pokemon(key, level=level)
    chosen_gender = gender or instance.gender
    chosen_nature = nature or instance.nature
    pokemon = create_owned_pokemon(
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
        active_move_names=list(getattr(instance, "moves", []) or []),
    )
    ensure_boxes(char.storage).add_active_pokemon(pokemon)
    return pokemon

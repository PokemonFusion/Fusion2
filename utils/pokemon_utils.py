import math
from evennia import create_object
from typeclasses.pokemon import Pokemon
from fusion2.pokemon.pokedex import pokedex
from utils.id_tracker_utils import get_id_tracker
from fusion2.pokemon.dex.natures import natures_dict
import random
import string

BASE36 = string.digits + string.ascii_uppercase

def base10_to_base36(num, min_length=4):
    """
    Convert a base-10 number to a base-36 string and format it.
    
    :param num: The base-10 number to convert.
    :param min_length: The minimum length of the output string (default is 4).
    :return: A formatted base-36 encoded string.
    """
    if num < 0:
        raise ValueError("Number must be non-negative")
    
    # Convert the number to base-36
    base36_str = ""
    while num:
        num, rem = divmod(num, 36)
        base36_str = BASE36[rem] + base36_str
    
    # Ensure the string is at least min_length characters long
    base36_str = base36_str.rjust(min_length, '0')
    
    # Format the string based on its length
    length = len(base36_str)
    if length == 4:
        formatted_str = f"{base36_str[:2]}-{base36_str[2:]}"
    elif length == 5:
        formatted_str = f"({base36_str[0]})-{base36_str[1:3]}-{base36_str[3:]}"
    elif length == 6:
        formatted_str = f"({base36_str[:2]})-{base36_str[2:4]}-{base36_str[4:]}"
    else:
        # For lengths greater than 6, include extra characters in parentheses
        extra_chars = length - 4
        formatted_str = f"({base36_str[:extra_chars]})-{base36_str[extra_chars:extra_chars+2]}-{base36_str[extra_chars+2:]}"
    
    return formatted_str

def base36_to_base10(formatted_str):
    """
    Convert a formatted base-36 string back to a base-10 number.
    
    :param formatted_str: The formatted base-36 string to convert.
    :return: The base-10 number.
    """
    # Remove parentheses and hyphens
    cleaned_str = formatted_str.replace('(', '').replace(')', '').replace('-', '')
    
    # Convert from base-36 to base-10
    base10_num = 0
    for char in cleaned_str:
        base10_num = base10_num * 36 + BASE36.index(char)
    
    return base10_num

def create_pokemon(name, owner=None, level=1):
    if name not in pokedex:
        raise ValueError(f"Pokémon {name} not found in Pokedex.")
    
    static_data = pokedex[name]
    pokedex_number = list(pokedex.keys()).index(name) + 1
    tracker = get_id_tracker()
    pokemon_id = tracker.get_next_id("player")
    encoded_id = base10_to_base36(pokemon_id)
    
    ivs = {stat: random.randint(0, 31) for stat in ['hp', 'attack', 'defense', 'sp_attack', 'sp_defense', 'speed']}
    evs = {stat: 0 for stat in ['hp', 'attack', 'defense', 'sp_attack', 'sp_defense', 'speed']}
    nature = "Hardy"  # Assign a default nature or randomly pick one from the list of natures
    
    pokemon = create_object(Pokemon, key=name)
    pokemon.set_static_data(static_data)
    pokemon.set_dynamic_data(
        pokemon_id=encoded_id,
        pokedex_number=pokedex_number,
        owner=owner,
        level=level,
        exp=0,
        current_hp=static_data['baseStats']['hp'],
        known_moves=[],
        ivs=ivs,
        evs=evs,
        nature=nature
    )
    return pokemon

def transfer_pokemon(pokemon, new_owner):
    if new_owner.is_typeclass("typeclasses.characters.Character", exact=True):
        tracker = get_id_tracker()
        new_id = tracker.get_next_id("player")
        encoded_id = base10_to_base36(new_id)
        pokemon.db.pokemon_id = encoded_id
        pokemon.db.category = "player"
    pokemon.db.owner = new_owner
    pokemon.db.caught = True

def delete_pokemon(pokemon):
    tracker = get_id_tracker()
    id_str = pokemon.db.pokemon_id
    id_number = sum(BASE36.index(c) * (36 ** i) for i, c in enumerate(reversed(id_str)))
    category = pokemon.db.category

    tracker.return_id(category, id_number)
    pokemon.delete()

def calculate_stat(base, iv, ev, level, nature, stat_type):
    """
    Calculate a Pokémon's stat.
    
    :param base: Base stat value.
    :param iv: Individual value (IV) for the stat.
    :param ev: Effort value (EV) for the stat.
    :param level: Level of the Pokémon.
    :param nature: Nature affecting the stat.
    :param stat_type: Type of the stat (e.g., 'hp', 'attack', etc.).
    :return: Calculated stat value.
    """
    if stat_type == 'hp':
        stat = ((2 * base + iv + (ev // 4)) * level // 100) + level + 10
    else:
        nature_modifier = natures_dict[nature]["multipliers"][stat_type]
        stat = (((2 * base + iv + (ev // 4)) * level // 100) + 5) * nature_modifier
    return math.floor(stat)
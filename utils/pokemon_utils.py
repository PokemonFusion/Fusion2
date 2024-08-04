import random
import math
from evennia import create_object
from typeclasses.pokemon import Pokemon
from fusion2.pokemon.pokedex import pokedex
from fusion2.pokemon.dex import parsed_learnset as pl
from utils.id_tracker_utils import get_id_tracker
import string

BASE36 = string.digits + string.ascii_uppercase

NATURES = {
    "Hardy": {},
    "Lonely": {'atk': 1.1, 'def': 0.9},
    "Brave": {'atk': 1.1, 'spe': 0.9},
    "Adamant": {'atk': 1.1, 'spa': 0.9},
    "Naughty": {'atk': 1.1, 'spd': 0.9},
    "Bold": {'def': 1.1, 'atk': 0.9},
    "Docile": {},
    "Relaxed": {'def': 1.1, 'spe': 0.9},
    "Impish": {'def': 1.1, 'spa': 0.9},
    "Lax": {'def': 1.1, 'spd': 0.9},
    "Timid": {'spe': 1.1, 'atk': 0.9},
    "Hasty": {'spe': 1.1, 'def': 0.9},
    "Serious": {},
    "Jolly": {'spe': 1.1, 'spa': 0.9},
    "Naive": {'spe': 1.1, 'spd': 0.9},
    "Modest": {'spa': 1.1, 'atk': 0.9},
    "Mild": {'spa': 1.1, 'def': 0.9},
    "Quiet": {'spa': 1.1, 'spe': 0.9},
    "Bashful": {},
    "Rash": {'spa': 1.1, 'spd': 0.9},
    "Calm": {'spd': 1.1, 'atk': 0.9},
    "Gentle": {'spd': 1.1, 'def': 0.9},
    "Sassy": {'spd': 1.1, 'spe': 0.9},
    "Careful": {'spd': 1.1, 'spa': 0.9},
    "Quirky": {},
}

STATUSES = {
    0: "Normal",
    1: "Burn",
    2: "Freeze",
    3: "Paralysis",
    4: "Poison",
    5: "Sleep",
    6: "Toxic",
    7: "Fainted"
}
STATUSES_SHORT = {
    0: "NRM",
    1: "BRN",
    2: "FRZ",
    3: "PAR",
    4: "PSN",
    5: "SLP",
    6: "TOX",
    7: "FNT"
}

STATUSES_REVERSE_SHORT = {
    "NRM": 0,
    "BRN": 1,
    "FRZ": 2,
    "PAR": 3,
    "PSN": 4,
    "SLP": 5,
    "TOX": 6,
    "FNT": 7
}

def get_status_effect(status: int):
    if status == 0:
        return 0, -1
    elif status == 1:
        return 1, -1
    elif status == 2:
        return 2, -1
    elif status == 3:
        return 3, -1
    elif status == 4:
        return 4, -1
    elif status == 5:
        return 5, random.randint(1, 3)
    elif status == 6:
        return 6, 1
    elif status == 7:
        return 7, -1
    else:
        return 0, -1  # Default to normal if unknown status

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
        nature_modifier = NATURES[nature].get(stat_type, 1.0)
        stat = (((2 * base + iv + (ev // 4)) * level // 100) + 5) * nature_modifier
    return math.floor(stat)

def generate_ivs():
    return {stat: random.randint(0, 31) for stat in ['hp', 'attack', 'defense', 'sp_attack', 'sp_defense', 'speed']}

def get_xp_rate(species):
    rate = get_dic_entry(species, "growthRateId")
    ratedict = {
        1: "slow",
        2: "mediumfast",
        3: "fast",
        4: "mediumslow",
        5: "erratic",
        6: "fluctuating"
    }
    return ratedict.get(rate)

def get_xp_to_level(level, xprate):
    if level == 1:
        return 0
    if xprate == 'erratic':
        if level <= 50:
            return int((level * level * level * (100 - level)) / 50)
        elif level <= 68:
            return int((level * level * level * (150 - level)) / 100)
        elif level <= 98:
            return int((level * level * level * int((1911 - (10 * level)) / 3)) / 100)
        else:
            return int((level * level * level * (160 - level)) / 100)
    elif xprate == 'fast':
        return int(4 * level * level * level / 5)
    elif xprate == 'mediumfast':
        return level * level * level
    elif xprate == 'mediumslow':
        return int((6 * level * level * level / 5) - (15 * level * level) + (100 * level) - 140)
    elif xprate == 'slow':
        return int(5 * level * level * level / 4)
    else:  # fluctuating
        if level <= 15:
            return int(level * level * level * ((int((level + 1) / 3) + 24) / 50))
        elif level <= 36:
            return int(level * level * level * ((level + 14) / 50))
        else:
            return int(level * level * level * ((int(level / 2) + 32) / 50))

def get_dic_entry(species, keyName):
    entry = get_dic(species).get(keyName)
    if entry is None and keyName != "baseSpecies":
        entry = get_dic(get_dic_entry(species, "baseSpecies")).get(keyName)
    return entry

def get_dic(species):
    return pokedex.get(species.lower(), pokedex["missingno"])

def team_generation(specify=False, team=None):
    """
    Generate a team of Pokémon.

    :param specify: If the moves and abilities should be specified or not.
    :param team: List of lists for the team: [['name', lvl], ... ]
    :return: A list of Pokémon objects representing the team.
    """
    if team is None:
        return []

    full_team = []
    for member in team:
        name, level = member
        team_poke = create_pokemon(name, owner=0, level=level)
        poke_moves = level_moves(name, level)
        move_index = 0
        for m in range(level):
            if move_index == 4:
                break
            try:
                for n in range(len(poke_moves[level - m])):
                    team_poke.move_sets[0][move_index] = poke_moves[level - m][n]
                    move_index += 1
                    if move_index == 4:
                        break
            except KeyError:
                continue
            except IndexError:
                continue
        full_team.append(team_poke)
    return full_team

def can_learn_move(pokemon, move, method):
    learnset = pl.pfLearnset
    if move.lower() in learnset[pokemon.lower()][method.lower()]:
        return True
    return False

def level_moves(pokemon, level):
    learnset = pl.pfLearnset
    moveList = {}
    try:
        target = learnset[pokemon.lower()]['level']
        for i in range(1, level):
            try:
                if "," in target[f'{i}']:
                    atkList = target[f'{i}'].split(",")
                    moveList.update({i: atkList})
                else:
                    moveList.update({i: [target[f'{i}']]})
            except KeyError:
                continue
    except KeyError:
        return ['None', 'None', 'None', 'None']
    return moveList
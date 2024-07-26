# fusion2/pokemon/middleware.py

from fusion2.pokemon.pokedex import pokedex

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

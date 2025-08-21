"""Helpers for determining egg species when breeding Pokémon.

The example below mirrors the instructions given in ``README.md`` and shows
how to look up the species that will hatch from two parents::

    from pokemon.data.generation import generate_pokemon
    from pokemon.data.breeding import determine_egg_species

    mom = generate_pokemon("Pikachu", level=10)
    dad = generate_pokemon("Ditto", level=10)
    egg = determine_egg_species(mom, dad)
    print(egg)  # -> "Pichu"
"""

from .generation import PokemonInstance
from ..dex import POKEDEX

# Mapping of male-only species to the female species that lays their eggs
_SPECIAL_MOTHERS = {
    "Nidoran-M": "Nidoran-F",
    "Nidorino": "Nidoran-F",
    "Nidoking": "Nidoran-F",
    "Volbeat": "Illumise",
    "Indeedee": "Indeedee-F",
}

# Species that produce different baby forms when an incense is held
_INCENSE_BABIES = {
    "Chansey": "Happiny",
    "Blissey": "Happiny",
    "Roselia": "Budew",
    "Roserade": "Budew",
    "Sudowoodo": "Bonsly",
    "Mr. Mime": "Mime Jr.",
    "Mr. Mime-Galar": "Mime Jr.",
    "Snorlax": "Munchlax",
    "Wobbuffet": "Wynaut",
    "Marill": "Azurill",
    "Azumarill": "Azurill",
    "Mantine": "Mantyke",
    "Chimecho": "Chingling",
}

__all__ = ["determine_egg_species"]


def _lookup_species(name: str):
    return (
        POKEDEX.get(name)
        or POKEDEX.get(name.lower())
        or POKEDEX.get(name.capitalize())
    )


def _get_base_form(species_name: str) -> str:
    """Return the base form for the given species by following ``prevo`` links."""
    current = _lookup_species(species_name)
    while current and current.prevo:
        prev = _lookup_species(current.prevo)
        if not prev:
            break
        current = prev
    return current.name if current else species_name


def determine_egg_species(parent_a: PokemonInstance, parent_b: PokemonInstance) -> str:
    """Return the species name that will hatch from these parents.

    Raises ``ValueError`` if the parents cannot breed.
    """

    def species_from_inst(inst: PokemonInstance):
        return _lookup_species(getattr(inst.species, "name", str(inst.species)))

    a = species_from_inst(parent_a)
    b = species_from_inst(parent_b)

    if not a or not b:
        raise ValueError("Unknown species")

    if "Undiscovered" in a.egg_groups or "Undiscovered" in b.egg_groups:
        raise ValueError("Incompatible egg groups")

    # Ditto handling
    if a.name == "Ditto":
        other = b
    elif b.name == "Ditto":
        other = a
    else:
        other = None

    if other:
        base = _get_base_form(_SPECIAL_MOTHERS.get(other.name, other.name))
        return _INCENSE_BABIES.get(base, base)

    # gender compatibility
    genders = {parent_a.gender, parent_b.gender}
    if "N" in genders or len(genders) != 2:
        raise ValueError("Incompatible genders")

    # shared egg group
    if not set(a.egg_groups).intersection(b.egg_groups):
        raise ValueError("Incompatible egg groups")

    female = parent_a if parent_a.gender == "F" else parent_b
    species = species_from_inst(female)
    if not species:
        raise ValueError("Unknown species")

    base_name = _SPECIAL_MOTHERS.get(species.name, species.name)
    base = _get_base_form(base_name)
    return _INCENSE_BABIES.get(base, base)

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

from pokemon.names import normalize_name, resolve_dex_entry

from ..dex import POKEDEX
from .generation import PokemonInstance

# These require random counterpart/form rules, rather than a fixed "mother".
_SPECIAL_OFFSPRING = {"nidoranf", "nidoranm", "nidorina", "nidorino", "nidoqueen", "nidoking",
                      "volbeat", "illumise", "indeedee", "indeedeef"}

# Generation 9 always produces these babies; an incense is not required.
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
    """Resolve stored keys and display names to the same breeding species."""
    return resolve_dex_entry(POKEDEX, name)


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

    if parent_a.gender not in {"M", "F", "N"} or parent_b.gender not in {"M", "F", "N"}:
        raise ValueError("Invalid parent gender")
    if a.name == b.name == "Ditto":
        raise ValueError("Two Ditto cannot produce an egg")
    if any(normalize_name(species.name) in _SPECIAL_OFFSPRING for species in (a, b)):
        raise ValueError("Special offspring families require an explicit counterpart/form rule")

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
        base = _get_base_form(other.name)
        return _INCENSE_BABIES.get(base, base)

    # gender compatibility
    genders = {parent_a.gender, parent_b.gender}
    if genders != {"M", "F"}:
        raise ValueError("Incompatible genders")

    # shared egg group
    if not set(a.egg_groups).intersection(b.egg_groups):
        raise ValueError("Incompatible egg groups")

    female = parent_a if parent_a.gender == "F" else parent_b
    species = species_from_inst(female)
    if not species:
        raise ValueError("Unknown species")

    base = _get_base_form(species.name)
    return _INCENSE_BABIES.get(base, base)

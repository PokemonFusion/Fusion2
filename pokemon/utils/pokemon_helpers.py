# Utility functions for working with Pokémon data.

from pokemon.generation import generate_pokemon
from pokemon.stats import calculate_stats


def _get_stats_from_data(pokemon):
    """Return calculated stats based on stored attributes."""
    ivs_attr = getattr(pokemon, "ivs", [0, 0, 0, 0, 0, 0])
    evs_attr = getattr(pokemon, "evs", [0, 0, 0, 0, 0, 0])
    if isinstance(ivs_attr, dict):
        ivs = {k: ivs_attr.get(k, 0) for k in ["hp", "atk", "def", "spa", "spd", "spe"]}
    else:
        ivs = {
            "hp": ivs_attr[0],
            "atk": ivs_attr[1],
            "def": ivs_attr[2],
            "spa": ivs_attr[3],
            "spd": ivs_attr[4],
            "spe": ivs_attr[5],
        }
    if isinstance(evs_attr, dict):
        evs = {k: evs_attr.get(k, 0) for k in ["hp", "atk", "def", "spa", "spd", "spe"]}
    else:
        evs = {
            "hp": evs_attr[0],
            "atk": evs_attr[1],
            "def": evs_attr[2],
            "spa": evs_attr[3],
            "spd": evs_attr[4],
            "spe": evs_attr[5],
        }
    nature = getattr(pokemon, "nature", "Hardy")
    species = getattr(pokemon, "species", getattr(pokemon, "name", ""))
    level = getattr(pokemon, "level", 1)
    try:
        return calculate_stats(species, level, ivs, evs, nature)
    except Exception:
        inst = generate_pokemon(species, level=level)
        return {
            "hp": inst.stats.hp,
            "atk": inst.stats.atk,
            "def": inst.stats.def_,
            "spa": inst.stats.spa,
            "spd": inst.stats.spd,
            "spe": inst.stats.spe,
        }


def get_max_hp(pokemon) -> int:
    """Return the calculated maximum HP for ``pokemon``."""
    stats = _get_stats_from_data(pokemon)
    return stats.get("hp", 0)


def get_stats(pokemon):
    """Return a dict of calculated stats for ``pokemon``."""
    return _get_stats_from_data(pokemon)


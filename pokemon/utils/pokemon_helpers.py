# Utility functions for working with Pokémon data.

from pokemon.generation import generate_pokemon
from pokemon.stats import calculate_stats


def _get_stats_from_data(pokemon):
    """Return calculated stats based on stored data."""
    data = getattr(pokemon, "data", {}) or {}
    if not data and hasattr(pokemon, "ivs"):
        ivs = {
            "hp": pokemon.ivs[0],
            "atk": pokemon.ivs[1],
            "def": pokemon.ivs[2],
            "spa": pokemon.ivs[3],
            "spd": pokemon.ivs[4],
            "spe": pokemon.ivs[5],
        }
        evs = {
            "hp": pokemon.evs[0],
            "atk": pokemon.evs[1],
            "def": pokemon.evs[2],
            "spa": pokemon.evs[3],
            "spd": pokemon.evs[4],
            "spe": pokemon.evs[5],
        }
        nature = getattr(pokemon, "nature", "Hardy")
        name = getattr(pokemon, "species", getattr(pokemon, "name", ""))
        level = getattr(pokemon, "level", 1)
    else:
        ivs = data.get("ivs", {})
        evs = data.get("evs", {})
        nature = data.get("nature", "Hardy")
        name = getattr(pokemon, "name", getattr(pokemon, "species", ""))
        level = getattr(pokemon, "level", 1)
    try:
        return calculate_stats(name, level, ivs, evs, nature)
    except Exception:
        inst = generate_pokemon(name, level=level)
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


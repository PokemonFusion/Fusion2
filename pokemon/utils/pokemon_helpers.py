# Utility functions for working with Pokémon data.

from pokemon.generation import generate_pokemon
from pokemon.stats import calculate_stats, STAT_KEY_MAP


def _get_stats_from_data(pokemon):
    """Return calculated stats based on stored attributes."""
    ivs_attr = getattr(pokemon, "ivs", [0, 0, 0, 0, 0, 0])
    evs_attr = getattr(pokemon, "evs", [0, 0, 0, 0, 0, 0])
    if isinstance(ivs_attr, dict):
        ivs = {STAT_KEY_MAP.get(k, k): v for k, v in ivs_attr.items()}
        ivs = {stat: ivs.get(stat, 0) for stat in STAT_KEY_MAP.values()}
    else:
        ivs = {
            "hp": ivs_attr[0],
            "attack": ivs_attr[1],
            "defense": ivs_attr[2],
            "special_attack": ivs_attr[3],
            "special_defense": ivs_attr[4],
            "speed": ivs_attr[5],
        }
    if isinstance(evs_attr, dict):
        evs = {STAT_KEY_MAP.get(k, k): v for k, v in evs_attr.items()}
        evs = {stat: evs.get(stat, 0) for stat in STAT_KEY_MAP.values()}
    else:
        evs = {
            "hp": evs_attr[0],
            "attack": evs_attr[1],
            "defense": evs_attr[2],
            "special_attack": evs_attr[3],
            "special_defense": evs_attr[4],
            "speed": evs_attr[5],
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
            "attack": inst.stats.attack,
            "defense": inst.stats.defense,
            "special_attack": inst.stats.special_attack,
            "special_defense": inst.stats.special_defense,
            "speed": inst.stats.speed,
        }


def get_max_hp(pokemon) -> int:
    """Return the calculated maximum HP for ``pokemon``."""
    stats = _get_stats_from_data(pokemon)
    return stats.get("hp", 0)


def get_stats(pokemon):
    """Return a dict of calculated stats for ``pokemon``."""
    return _get_stats_from_data(pokemon)


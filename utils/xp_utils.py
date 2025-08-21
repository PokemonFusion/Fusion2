"""XP utility helpers for sheet display."""

from pokemon.models.stats import level_for_exp, exp_for_level
from pokemon.utils.pokemon_like import PokemonLike

__all__ = ["get_display_xp", "get_next_level_xp"]


def get_display_xp(pokemon: PokemonLike) -> int:
    """Return the experience total for ``pokemon``."""

    for attr in ("xp", "experience", "total_exp"):
        val = getattr(pokemon, attr, None)
        if val is not None:
            return int(val)
    return 0


def get_next_level_xp(pokemon: PokemonLike) -> int:
    """Return the experience needed for the next level."""

    xp = get_display_xp(pokemon)

    growth = getattr(pokemon, "growth_rate", "medium_fast")

    level = level_for_exp(xp, growth)
    next_level = min(level + 1, 100)
    return exp_for_level(next_level, growth)

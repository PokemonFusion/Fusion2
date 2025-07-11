"""XP utility helpers for sheet display."""

from pokemon.stats import level_for_exp, exp_for_level

__all__ = ["get_display_xp", "get_next_level_xp"]


def get_display_xp(pokemon) -> int:
    """Return the experience total for ``pokemon``."""
    return getattr(
        pokemon,
        "xp",
        getattr(pokemon, "experience", getattr(pokemon, "total_exp", 0)),
    )


def get_next_level_xp(pokemon) -> int:
    """Return the experience needed for the next level."""
    xp = get_display_xp(pokemon)
    growth = getattr(pokemon, "growth_rate", "medium_fast")
    level = level_for_exp(xp, growth)
    next_level = min(level + 1, 100)
    return exp_for_level(next_level, growth)

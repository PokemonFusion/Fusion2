"""Utility helpers for the battle engine."""

from typing import Dict


def apply_boost(pokemon, boosts: Dict[str, int]) -> None:
    """Modify a Pokémon's stat stages, clamped between -6 and 6."""

    if not hasattr(pokemon, "boosts"):
        return

    for stat, amount in boosts.items():
        current = pokemon.boosts.get(stat, 0)
        pokemon.boosts[stat] = max(-6, min(6, current + amount))


"""Utility helpers for the battle engine."""

from typing import Dict



def apply_boost(pokemon, boosts: Dict[str, int]) -> None:
    """Modify a Pokémon's stat stages, clamped between -6 and 6."""

    if not hasattr(pokemon, "boosts"):
        return

    for stat, amount in boosts.items():
        current = pokemon.boosts.get(stat, 0)
        pokemon.boosts[stat] = max(-6, min(6, current + amount))


def get_modified_stat(pokemon, stat: str) -> int:
    """Return a stat value after applying temporary boosts."""

    try:
        from pokemon.utils.pokemon_helpers import get_stats
        base = get_stats(pokemon).get(stat, 0)
    except Exception:
        base = getattr(getattr(pokemon, "base_stats", None), stat, 0)
    boosts = getattr(pokemon, "boosts", {})
    if isinstance(boosts, dict):
        stage = boosts.get(stat, 0)
    else:
        stage = getattr(boosts, stat, 0)

    if stat in {"accuracy", "evasion"}:
        if stage >= 0:
            modifier = (3 + stage) / 3
        else:
            modifier = 3 / (3 - stage)
    else:
        if stage >= 0:
            modifier = (2 + stage) / 2
        else:
            modifier = 2 / (2 - stage)
    return int(base * modifier)


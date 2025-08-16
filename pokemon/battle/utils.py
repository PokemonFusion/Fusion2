"""Utility helpers for the battle engine."""

from typing import Dict

from pokemon.utils.boosts import STAT_KEY_MAP, apply_boost


def _safe_get_stats(pokemon) -> Dict[str, int]:
    """Return a stats dictionary for ``pokemon`` with graceful fallback.

    The standard :func:`helpers.pokemon_helpers.get_stats` helper is
    used when available.  If that import or call fails, the function falls
    back to the Pokémon's ``base_stats`` attribute, ensuring that callers
    always receive a dictionary of stat values.
    """

    try:  # pragma: no cover - import error path
        from helpers.pokemon_helpers import get_stats
        return get_stats(pokemon)
    except Exception:  # pragma: no cover - broad fallback
        base = getattr(pokemon, "base_stats", None)
        if isinstance(base, dict):
            return {STAT_KEY_MAP.get(k, k): v for k, v in base.items()}
        return {name: getattr(base, name, 0) if base else 0 for name in STAT_KEY_MAP.values()}


def get_modified_stat(pokemon, stat: str) -> int:
    """Return a stat value after applying temporary boosts."""

    stat = STAT_KEY_MAP.get(stat, stat)
    base = _safe_get_stats(pokemon).get(stat, 0)
    boosts = getattr(pokemon, "boosts", {})
    if isinstance(boosts, dict):
        boosts = {STAT_KEY_MAP.get(k, k): v for k, v in boosts.items()}
        pokemon.boosts = boosts
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


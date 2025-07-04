"""Convenience imports for the pokemon package."""

try:
    from .generation import generate_pokemon, choose_wild_moves, PokemonInstance
except Exception:  # pragma: no cover - optional for lightweight test stubs
    generate_pokemon = None
    choose_wild_moves = None
    PokemonInstance = None

from .evolution import get_evolution_items, get_evolution, attempt_evolution
from .stats import (
    exp_for_level,
    level_for_exp,
    add_experience,
    add_evs,
    calculate_stats,
    distribute_experience,
    award_experience_to_party,
)

__all__ = [
    "generate_pokemon",
    "choose_wild_moves",
    "PokemonInstance",
    "exp_for_level",
    "level_for_exp",
    "add_experience",
    "add_evs",
    "calculate_stats",
    "distribute_experience",
    "award_experience_to_party",
    "get_evolution_items",
    "get_evolution",
    "attempt_evolution",
]

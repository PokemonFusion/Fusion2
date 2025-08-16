"""Convenience imports for the pokemon package."""

try:
    from .generation import generate_pokemon, choose_wild_moves, PokemonInstance
except Exception:  # pragma: no cover - optional for lightweight test stubs
    generate_pokemon = None
    choose_wild_moves = None
    PokemonInstance = None

from .evolution import get_evolution_items, get_evolution, attempt_evolution
try:
    from .breeding import determine_egg_species
except Exception:  # pragma: no cover - optional for lightweight test stubs
    determine_egg_species = None
try:
    from .stats import (
        exp_for_level,
        level_for_exp,
        add_experience,
        add_evs,
        calculate_stats,
        distribute_experience,
        award_experience_to_party,
    )
except Exception:  # pragma: no cover - optional for lightweight test stubs
    exp_for_level = level_for_exp = add_experience = None
    add_evs = calculate_stats = distribute_experience = None
    award_experience_to_party = None

try:
	from .testfactory import make_test_pokemon, make_punching_bag
except Exception:  # pragma: no cover - optional for lightweight test stubs
	make_test_pokemon = make_punching_bag = None

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
    "determine_egg_species",
	"make_test_pokemon",
	"make_punching_bag",
]

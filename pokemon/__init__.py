"""Convenience imports for the pokemon package."""

try:
	from .data.generation import (
		PokemonInstance,
		choose_wild_moves,
		generate_pokemon,
	)
except Exception:  # pragma: no cover - optional for lightweight test stubs
	generate_pokemon = None
	choose_wild_moves = None
	PokemonInstance = None

from .data.evolution import attempt_evolution, get_evolution, get_evolution_items

try:
	from .data.breeding import determine_egg_species
except Exception:  # pragma: no cover - optional for lightweight test stubs
	determine_egg_species = None
try:
	from .models.stats import (
		add_evs,
		add_experience,
		award_experience_to_party,
		calculate_stats,
		distribute_experience,
		exp_for_level,
		level_for_exp,
	)
except Exception:  # pragma: no cover - optional for lightweight test stubs
	exp_for_level = level_for_exp = add_experience = None
	add_evs = calculate_stats = distribute_experience = None
	award_experience_to_party = None

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
]

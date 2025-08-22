"""Faction helper stubs for sheet display."""

__all__ = ["get_faction_and_rank"]

from pokemon.utils.pokemon_like import PokemonLike


def get_faction_and_rank(pokemon: PokemonLike) -> str:
	"""Return formatted faction and rank information."""
	# TODO: connect to real faction system
	faction = getattr(pokemon, "faction", None)
	rank = getattr(pokemon, "faction_rank", None)
	if faction:
		return f"{faction} ({rank})" if rank else faction
	return "None"

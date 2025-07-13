"""Helper functions for display utilities."""

from pokemon.utils.pokemon_like import PokemonLike

__all__ = [
    "get_status_effects",
    "format_move_details",
    "get_egg_description",
]


def get_status_effects(pokemon: PokemonLike) -> str:
    """Return a short status string for ``pokemon``."""
    status = getattr(pokemon, "status", None)
    return status or "NORM"


def get_egg_description(hatch: int) -> str:
    """Return description text based on hatch progress."""
    # TODO: implement proper egg status checks
    return ""  # placeholder


def format_move_details(move) -> str:
    """Return a formatted move detail line."""
    # TODO: include move class, type, power, accuracy and description
    name = getattr(move, "name", str(move))
    pp = getattr(move, "pp", getattr(move, "current_pp", None))
    max_pp = getattr(move, "max_pp", None)
    if pp is not None and max_pp is not None:
        return f"{name} ({pp}/{max_pp} PP)"
    if pp is not None:
        return f"{name} ({pp} PP)"
    return name

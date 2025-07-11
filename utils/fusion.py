"""Helper functions for managing Pokémon fusions."""

from pokemon.models import PokemonFusion


def record_fusion(result, parent_a, parent_b):
    """Create a fusion record linking ``parent_a`` and ``parent_b`` to ``result``."""
    return PokemonFusion.objects.create(result=result, parent_a=parent_a, parent_b=parent_b)


def get_fusion_parents(result):
    """Return the parent Pokémon for ``result`` if a fusion record exists."""
    entry = PokemonFusion.objects.filter(result=result).first()
    if entry:
        return entry.parent_a, entry.parent_b
    return None, None

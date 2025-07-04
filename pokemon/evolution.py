from typing import List, Optional

from .dex import POKEDEX

__all__ = ["get_evolution_items", "get_evolution", "attempt_evolution"]


def get_evolution_items() -> List[str]:
    """Return a sorted list of items that trigger evolutions."""
    items = set()
    for data in POKEDEX.values():
        item = data.raw.get("evoItem")
        if item:
            items.add(item)
    return sorted(items)


def get_evolution(species: str, *, level: int, item: Optional[str] = None) -> Optional[str]:
    """Return the name of the evolved species if conditions are met."""
    def lookup(name: str):
        return (
            POKEDEX.get(name)
            or POKEDEX.get(name.capitalize())
            or POKEDEX.get(name.lower())
        )

    current = lookup(species)
    if not current:
        return None
    for evo_name in current.evos:
        evo = lookup(evo_name)
        if not evo:
            continue
        e_type = evo.raw.get("evoType")
        e_item = evo.raw.get("evoItem")
        e_level = evo.evo_level
        if e_type == "useItem":
            if item and e_item and item.lower() == e_item.lower():
                return evo.name
        elif e_type in ("trade",):
            continue
        else:
            req_level = e_level or 0
            if level >= req_level:
                return evo.name
    return None


def attempt_evolution(pokemon, *, item: Optional[str] = None) -> Optional[str]:
    """Evolve the given Pokemon object if possible.

    Args:
        pokemon: An object with at least ``name`` and ``level`` attributes.
        item: Optional evolution item used.

    Returns:
        The name of the new species if evolution occurred, else ``None``.
    """
    species = pokemon.name
    level = getattr(pokemon, "level", 0)
    target = get_evolution(species, level=level, item=item)
    if not target:
        return None
    data = POKEDEX.get(target.lower())
    pokemon.name = target
    if hasattr(pokemon, "type_") and data:
        pokemon.type_ = ", ".join(data.types)
    if hasattr(pokemon, "data") and data:
        pokemon.data.update(data.raw)
    return target

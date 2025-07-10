"""Faction helper stubs for sheet display."""

__all__ = ["get_faction_and_rank"]


def get_faction_and_rank(pokemon) -> str:
    """Return formatted faction and rank information."""
    # TODO: connect to real faction system
    faction = getattr(pokemon, "faction", None)
    rank = getattr(pokemon, "faction_rank", None)
    if faction:
        return f"{faction} ({rank})" if rank else faction
    return "None"

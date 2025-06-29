"""Placeholder catch rate data for Pokémon species."""

CATCH_RATES = {
    # Species : catch rate
    'Bulbasaur': 45,
    # Add additional species here
}


def get_catch_rate(name: str) -> int:
    """Return the catch rate for a given species name."""
    return CATCH_RATES.get(name, 255)

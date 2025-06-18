"""Convenience imports for the pokemon package.

The heavy generation and dex modules are imported lazily so that
subpackages like ``pokemon.battle`` can be used without loading the
entire Pok\u00e9mon database during test collection.
"""

from importlib import import_module

__all__ = ["generate_pokemon", "PokemonInstance"]


def __getattr__(name):
    if name in __all__:
        mod = import_module(".generation", __name__)
        return getattr(mod, name)
    raise AttributeError(name)

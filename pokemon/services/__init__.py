"""Service layer for Pokémon-specific domain logic.

This package contains helper functions that sit between the database
models and higher level game code.  By centralising behaviour here we can
keep the models light-weight while still exposing convenient utilities.
"""

__all__ = ["capture", "move_management"]

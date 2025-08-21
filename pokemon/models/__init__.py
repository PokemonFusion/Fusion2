"""Convenience re-exports for Pokémon models."""

"""Database models and related utilities for the Pokémon game."""

from .validators import validate_ivs, validate_evs
from .enums import Gender, Nature

# The remaining model imports depend on Django/Evennia being available.  When
# running lightweight tests without the full environment configured we allow
# these imports to fail gracefully and expose ``None`` placeholders instead.
try:  # pragma: no cover - optional heavy dependencies
    from .core import (
        MAX_PP_MULTIPLIER,
        SpeciesEntry,
        BasePokemon,
        Pokemon,
        OwnedPokemon,
        BattleSlot,
    )
    from .moves import (
        Move,
        VerifiedMove,
        PokemonLearnedMove,
        Moveset,
        MovesetSlot,
        ActiveMoveslot,
        MovePPBoost,
    )
    from .trainer import Trainer, NPCTrainer, GymBadge, InventoryEntry
    from .storage import UserStorage, StorageBox, ActivePokemonSlot, ensure_boxes
    from .fusion import PokemonFusion
except Exception:  # pragma: no cover - used when ORM isn't set up
    MAX_PP_MULTIPLIER = SpeciesEntry = BasePokemon = Pokemon = OwnedPokemon = BattleSlot = None
    Move = VerifiedMove = PokemonLearnedMove = Moveset = MovesetSlot = ActiveMoveslot = MovePPBoost = None
    Trainer = NPCTrainer = GymBadge = InventoryEntry = None
    UserStorage = StorageBox = ActivePokemonSlot = ensure_boxes = None
    PokemonFusion = None

__all__ = [
    "MAX_PP_MULTIPLIER",
    "validate_ivs",
    "validate_evs",
    "Gender",
    "Nature",
    "SpeciesEntry",
    "BasePokemon",
    "Pokemon",
    "OwnedPokemon",
    "BattleSlot",
    "Move",
    "VerifiedMove",
    "PokemonLearnedMove",
    "Moveset",
    "MovesetSlot",
    "ActiveMoveslot",
    "MovePPBoost",
    "Trainer",
    "NPCTrainer",
    "GymBadge",
    "InventoryEntry",
    "UserStorage",
    "StorageBox",
    "ActivePokemonSlot",
    "ensure_boxes",
    "PokemonFusion",
]


"""Convenience re-exports for Pokémon models."""

# Import directly and relatively so Django always loads the model classes.
# Do NOT swallow ImportError here—if something breaks, we want to see it.

from .enums import Gender, Nature
from .validators import validate_evs, validate_ivs

# Core
from .core import (  # noqa: F401
    MAX_PP_MULTIPLIER,
    BasePokemon,
    BattleSlot,
    OwnedPokemon,
    Pokemon,
    SpeciesEntry,
)

# Fusion
from .fusion import PokemonFusion  # noqa: F401

# Moves
from .moves import (  # noqa: F401
    ActiveMoveslot,
    Move,
    MovePPBoost,
    Moveset,
    MovesetSlot,
    PokemonLearnedMove,
    VerifiedMove,
)

# Storage
from .storage import (  # noqa: F401
    ActivePokemonSlot,
    StorageBox,
    UserStorage,
    ensure_boxes,
)

# Trainer
from .trainer import (  # noqa: F401
    GymBadge,
    InventoryEntry,
    NPCTrainer,
    Trainer,
)

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


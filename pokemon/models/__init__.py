"""Convenience re-exports for Pokémon models.

Database models and related utilities for the Pokémon game.
"""

from .enums import Gender, Nature
from .validators import validate_evs, validate_ivs

# IMPORTANT: Do not swallow import errors here. Django must import these modules
# so the model classes get registered with the app. If something fails, we want
# it to fail loudly rather than silently returning ``None`` placeholders.

# Core Pokémon models -------------------------------------------------------
from .core import (  # noqa: F401
    MAX_PP_MULTIPLIER,
    BasePokemon,
    BattleSlot,
    OwnedPokemon,
    Pokemon,
    SpeciesEntry,
)

# Fusion -------------------------------------------------------------------
from .fusion import PokemonFusion  # noqa: F401

# Moves and related models --------------------------------------------------
from .moves import (  # noqa: F401
    ActiveMoveslot,
    Move,
    MovePPBoost,
    Moveset,
    MovesetSlot,
    PokemonLearnedMove,
    VerifiedMove,
)

# Storage ------------------------------------------------------------------
from .storage import (  # noqa: F401
    ActivePokemonSlot,
    StorageBox,
    UserStorage,
    ensure_boxes,
)

# Trainer ------------------------------------------------------------------
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

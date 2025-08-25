"""Convenience re-exports for Pokémon models.

Database models and related utilities for the Pokémon game.
"""

from django.core.exceptions import AppRegistryNotReady, ImproperlyConfigured

from .enums import Gender, Nature
from .validators import validate_evs, validate_ivs


# The remaining model imports depend on Django/Evennia being available.
# When running lightweight tests without the full environment configured we
# allow individual imports to fail gracefully and expose ``None`` placeholders
# instead.  Import errors in one module should not prevent others from loading
# successfully.  We therefore catch only configuration-related errors here so
# that unexpected problems surface rather than silently producing missing
# models during Django's system checks.

# Core Pokémon models -------------------------------------------------------
try:  # pragma: no cover - optional heavy dependencies
        from .core import (
                MAX_PP_MULTIPLIER,
                BasePokemon,
                BattleSlot,
                OwnedPokemon,
                Pokemon,
                SpeciesEntry,
        )
except (ImportError, ImproperlyConfigured, AppRegistryNotReady):  # pragma: no cover - used when ORM isn't set up
        (
                MAX_PP_MULTIPLIER,
                SpeciesEntry,
                BasePokemon,
                Pokemon,
                OwnedPokemon,
                BattleSlot,
        ) = (None,) * 6

# Fusion -------------------------------------------------------------------
try:  # pragma: no cover - optional heavy dependencies
        from .fusion import PokemonFusion
except (ImportError, ImproperlyConfigured, AppRegistryNotReady):  # pragma: no cover - used when ORM isn't set up
        PokemonFusion = None

# Moves and related models --------------------------------------------------
try:  # pragma: no cover - optional heavy dependencies
        from .moves import (
                ActiveMoveslot,
                Move,
                MovePPBoost,
                Moveset,
                MovesetSlot,
                PokemonLearnedMove,
                VerifiedMove,
        )
except (ImportError, ImproperlyConfigured, AppRegistryNotReady):  # pragma: no cover - used when ORM isn't set up
        (
                Move,
                VerifiedMove,
                PokemonLearnedMove,
                Moveset,
                MovesetSlot,
                ActiveMoveslot,
                MovePPBoost,
        ) = (None,) * 7

# Storage ------------------------------------------------------------------
try:  # pragma: no cover - optional heavy dependencies
        from .storage import (
                ActivePokemonSlot,
                StorageBox,
                UserStorage,
                ensure_boxes,
        )
except (ImportError, ImproperlyConfigured, AppRegistryNotReady):  # pragma: no cover - used when ORM isn't set up
        UserStorage = StorageBox = ActivePokemonSlot = ensure_boxes = None

# Trainer ------------------------------------------------------------------
try:  # pragma: no cover - optional heavy dependencies
        from .trainer import GymBadge, InventoryEntry, NPCTrainer, Trainer
except (ImportError, ImproperlyConfigured, AppRegistryNotReady):  # pragma: no cover - used when ORM isn't set up
        Trainer = NPCTrainer = GymBadge = InventoryEntry = None

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

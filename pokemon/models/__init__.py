"""Convenience re-exports for Pokémon models.

Database models and related utilities for the Pokémon game.
"""

from .enums import Gender, Nature
from .validators import validate_evs, validate_ivs

# The remaining model imports depend on Django/Evennia being available.  When
# running lightweight tests without the full environment configured we allow
# these imports to fail gracefully and expose ``None`` placeholders instead.
# Import each module individually so a failure in one doesn't prevent the
# others from registering with the Django app registry.

try:  # pragma: no cover - optional heavy dependencies
	from .core import (
		MAX_PP_MULTIPLIER,
		BasePokemon,
		BattleSlot,
		OwnedPokemon,
		Pokemon,
		SpeciesEntry,
	)
except Exception:  # pragma: no cover - used when ORM isn't set up
	(
		MAX_PP_MULTIPLIER,
		SpeciesEntry,
		BasePokemon,
		Pokemon,
		OwnedPokemon,
		BattleSlot,
	) = (None,) * 6

try:  # pragma: no cover - optional heavy dependencies
	from .fusion import PokemonFusion
except Exception:  # pragma: no cover - used when ORM isn't set up
	PokemonFusion = None

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
except Exception:  # pragma: no cover - used when ORM isn't set up
	(
		Move,
		VerifiedMove,
		PokemonLearnedMove,
		Moveset,
		MovesetSlot,
		ActiveMoveslot,
		MovePPBoost,
	) = (None,) * 7

try:  # pragma: no cover - optional heavy dependencies
	from .storage import (
		ActivePokemonSlot,
		StorageBox,
		UserStorage,
		ensure_boxes,
	)
except Exception:  # pragma: no cover - used when ORM isn't set up
	UserStorage = StorageBox = ActivePokemonSlot = ensure_boxes = None

try:  # pragma: no cover - optional heavy dependencies
	from .trainer import GymBadge, InventoryEntry, NPCTrainer, Trainer
except Exception:  # pragma: no cover - used when ORM isn't set up
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

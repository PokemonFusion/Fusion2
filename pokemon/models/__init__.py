"""Convenience re-exports for Pokémon models.

Database models and related utilities for the Pokémon game.
"""

from django.core.exceptions import AppRegistryNotReady, ImproperlyConfigured

from .enums import Gender, Nature
from .validators import validate_evs, validate_ivs


def _safe_import(module: str, names: list[str]):
    try:
        mod = __import__(module, fromlist=names)
        return [getattr(mod, n) for n in names]
    except (AppRegistryNotReady, ImproperlyConfigured, ImportError):
        return [None] * len(names)


# Core Pokémon models -------------------------------------------------------
(
    MAX_PP_MULTIPLIER,
    BasePokemon,
    BattleSlot,
    OwnedPokemon,
    Pokemon,
    SpeciesEntry,
) = _safe_import(
    "pokemon.models.core",
    [
        "MAX_PP_MULTIPLIER",
        "BasePokemon",
        "BattleSlot",
        "OwnedPokemon",
        "Pokemon",
        "SpeciesEntry",
    ],
)

# Fusion -------------------------------------------------------------------
(PokemonFusion,) = _safe_import("pokemon.models.fusion", ["PokemonFusion"])

# Moves and related models --------------------------------------------------
(
    ActiveMoveslot,
    Move,
    MovePPBoost,
    Moveset,
    MovesetSlot,
    PokemonLearnedMove,
    VerifiedMove,
) = _safe_import(
    "pokemon.models.moves",
    [
        "ActiveMoveslot",
        "Move",
        "MovePPBoost",
        "Moveset",
        "MovesetSlot",
        "PokemonLearnedMove",
        "VerifiedMove",
    ],
)

# Storage ------------------------------------------------------------------
(
    ActivePokemonSlot,
    StorageBox,
    UserStorage,
    ensure_boxes,
) = _safe_import(
    "pokemon.models.storage",
    ["ActivePokemonSlot", "StorageBox", "UserStorage", "ensure_boxes"],
)

# Trainer ------------------------------------------------------------------
(
    GymBadge,
    InventoryEntry,
    NPCTrainer,
    Trainer,
) = _safe_import(
    "pokemon.models.trainer",
    ["GymBadge", "InventoryEntry", "NPCTrainer", "Trainer"],
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

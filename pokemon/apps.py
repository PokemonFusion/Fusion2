"""App configuration for the Pokémon Django application."""

from django.apps import AppConfig


class PokemonConfig(AppConfig):
	"""Django application configuration for Pokémon models."""

	default_auto_field = "django.db.models.AutoField"
	name = "pokemon"

	def ready(self) -> None:  # pragma: no cover - import side effects
		# Import models submodules to ensure all models register with Django's
		# app registry even if this package was imported before settings were
		# configured. This avoids missing model errors at runtime.
		from . import models  # pylint: disable=unused-import
		from .models import core, fusion, moves, storage, trainer  # noqa: F401

		# Re-export key models for convenience.
		models.MAX_PP_MULTIPLIER = getattr(core, "MAX_PP_MULTIPLIER", None)
		models.BasePokemon = getattr(core, "BasePokemon", None)
		models.BattleSlot = getattr(core, "BattleSlot", None)
		models.OwnedPokemon = getattr(core, "OwnedPokemon", None)
		models.Pokemon = getattr(core, "Pokemon", None)
		models.SpeciesEntry = getattr(core, "SpeciesEntry", None)

		models.ActiveMoveslot = getattr(moves, "ActiveMoveslot", None)
		models.Move = getattr(moves, "Move", None)
		models.MovePPBoost = getattr(moves, "MovePPBoost", None)
		models.Moveset = getattr(moves, "Moveset", None)
		models.MovesetSlot = getattr(moves, "MovesetSlot", None)
		models.PokemonLearnedMove = getattr(moves, "PokemonLearnedMove", None)
		models.VerifiedMove = getattr(moves, "VerifiedMove", None)

		models.ActivePokemonSlot = getattr(storage, "ActivePokemonSlot", None)
		models.StorageBox = getattr(storage, "StorageBox", None)
		models.UserStorage = getattr(storage, "UserStorage", None)
		models.ensure_boxes = getattr(storage, "ensure_boxes", None)

		models.GymBadge = getattr(trainer, "GymBadge", None)
		models.InventoryEntry = getattr(trainer, "InventoryEntry", None)
		models.NPCTrainer = getattr(trainer, "NPCTrainer", None)
		models.Trainer = getattr(trainer, "Trainer", None)
		models.PokemonFusion = getattr(fusion, "PokemonFusion", None)

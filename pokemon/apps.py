"""App configuration for the Pokémon Django application."""

from importlib import import_module, reload

from django.apps import AppConfig, apps


class PokemonConfig(AppConfig):
	"""Django application configuration for Pokémon models."""

	default_auto_field = "django.db.models.AutoField"
	name = "pokemon"

	def ready(self) -> None:  # pragma: no cover - import side effects
		"""Load model submodules to guarantee Django registers them."""

		from . import models

		# If models have already been registered normally, skip the heavy
		# reload logic to avoid duplicate registrations that trigger
		# warnings during server reloads.
		registry = apps.all_models.get(self.label, {})
		if "moveset" in registry:
			return

		module_names = ("core", "fusion", "moves", "storage", "trainer")
		loaded = {}
		for name in module_names:
			# Reload modules to re-execute model declarations if this
			# package was imported before Django finished setting up.
			# Without this, early imports could leave the registry
			# without these models.
			module = reload(import_module(f"pokemon.models.{name}"))
			loaded[name] = module

		core = loaded["core"]
		fusion = loaded["fusion"]
		moves = loaded["moves"]
		storage = loaded["storage"]
		trainer = loaded["trainer"]

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

"""Helper functions for managing Pokémon fusions."""

from pokemon.models.fusion import PokemonFusion


def record_fusion(result, trainer, pokemon, permanent=False):
	"""Create or fetch a trainer/Pokémon fusion.

	Parameters
	----------
	result
	    The resulting ``OwnedPokemon`` instance.
	trainer
	    ``Trainer`` who fused with the Pokémon.
	pokemon
	    ``OwnedPokemon`` fused with ``trainer``.
	permanent
	    Whether this fusion is permanent.
	"""

	fusion, _ = PokemonFusion.objects.get_or_create(
		trainer=trainer,
		pokemon=pokemon,
		defaults={"result": result, "permanent": permanent},
	)
	storage = getattr(getattr(trainer, "user", None), "storage", None)
	if storage and result not in storage.active_pokemon.all():
		storage.add_active_pokemon(result)
	return fusion


def get_fusion_parents(result):
	"""Return the trainer and Pokémon for ``result`` if available."""
	entry = PokemonFusion.objects.filter(result=result).first()
	if entry:
		return entry.trainer, entry.pokemon
	return None, None

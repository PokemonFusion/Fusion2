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

	Raises
	------
	ValueError
	    If the trainer's active party is full and the fused Pokémon could
	    not be added.
	"""

	fusion, _ = PokemonFusion.objects.get_or_create(
	        trainer=trainer,
	        pokemon=pokemon,
	        defaults={"result": result, "permanent": permanent},
	)
	storage = getattr(getattr(trainer, "user", None), "storage", None)
	if storage and not getattr(result, "in_party", False):
	        try:
	                storage.add_active_pokemon(result)
	        except ValueError as err:
	                raise ValueError(f"Unable to add fused Pokémon to party: {err}") from err
	return fusion


def get_fusion_parents(result):
	"""Return the trainer and Pokémon for ``result`` if available."""
	entry = PokemonFusion.objects.filter(result=result).first()
	if entry:
		return entry.trainer, entry.pokemon
	return None, None

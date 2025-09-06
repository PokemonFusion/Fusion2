"""Utilities for handling trainer and Pokémon fusions.

The original fusion model was removed in migration 0034. These helpers now
perform minimal bookkeeping such as ensuring the fused Pokémon is added to a
trainer's party. They intentionally do not persist any database records.
"""

from typing import Any, Tuple

from pokemon.dex import POKEDEX


def record_fusion(result: Any, trainer: Any, pokemon: Any, permanent: bool = False) -> None:
    """Ensure ``result`` is present in ``trainer``'s active party.

    Parameters
    ----------
    result
        The fused :class:`~pokemon.models.core.OwnedPokemon` instance.
    trainer
        The owning trainer.
    pokemon
        The original Pokémon fused with the trainer. Kept for API compatibility.
    permanent
        Whether the fusion is permanent. Permanent fusions adopt the growth rate
        of the Pokémon they are fused with.
    """

    def _growth_from_pokemon(poke: Any) -> str:
        """Return the growth rate for ``poke``.

        This checks the object itself and falls back to the species data. If no
        information is available ``"medium_fast"`` is returned.
        """

        growth = getattr(poke, "growth_rate", None)
        if growth:
            return str(growth)
        name = getattr(poke, "species", getattr(poke, "name", None))
        if name:
            species = (
                POKEDEX.get(name)
                or POKEDEX.get(str(name).lower())
                or POKEDEX.get(str(name).capitalize())
            )
            if species:
                return species.raw.get("growthRate", "medium_fast")
        return "medium_fast"

    if permanent:
        setattr(result, "growth_rate", _growth_from_pokemon(pokemon))

    storage = getattr(getattr(trainer, "user", None), "storage", None)
    if storage and not getattr(result, "in_party", False):
        storage.add_active_pokemon(result)


def get_fusion_parents(result: Any) -> Tuple[Any, Any]:
    """Return ``(None, None)`` as fusion records are no longer stored."""

    return None, None

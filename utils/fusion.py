"""Utilities for handling trainer and Pokémon fusions.

The original fusion model was removed in migration 0034. These helpers now
perform minimal bookkeeping such as ensuring the fused Pokémon is added to a
trainer's party. They intentionally do not persist any database records.
"""

from typing import Any, Tuple


def record_fusion(result: Any, trainer: Any, pokemon: Any, permanent: bool = False) -> None:
    """Ensure ``result`` is present in ``trainer``'s active party.

    Parameters
    ----------
    result
        The fused :class:`~pokemon.models.core.OwnedPokemon` instance.
    trainer
        The owning trainer.
    pokemon
        The original Pokémon fused with the trainer.  Kept for API compatibility.
    permanent
        Whether the fusion is permanent. Permanent fusions level using the
        special ``"fusion"`` growth rate.
    """

    if permanent:
        setattr(result, "growth_rate", "fusion")

    storage = getattr(getattr(trainer, "user", None), "storage", None)
    if storage and not getattr(result, "in_party", False):
        storage.add_active_pokemon(result)


def get_fusion_parents(result: Any) -> Tuple[Any, Any]:
    """Return ``(None, None)`` as fusion records are no longer stored."""

    return None, None

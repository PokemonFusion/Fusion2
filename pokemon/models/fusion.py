"""Model representing a fusion between a trainer and a Pokémon."""

from django.db import models
import uuid


class PokemonFusion(models.Model):
    """Record a fusion between a trainer and a Pokémon."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trainer = models.ForeignKey(
        "Trainer",
        on_delete=models.CASCADE,
        related_name="pokemon_fusions",
        null=True,
        blank=True,
    )
    pokemon = models.ForeignKey(
        "OwnedPokemon",
        on_delete=models.CASCADE,
        related_name="trainer_fusions",
        null=True,
        blank=True,
    )
    result = models.OneToOneField(
        "OwnedPokemon",
        on_delete=models.CASCADE,
        related_name="fusion_result",
    )
    permanent = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["trainer", "pokemon"],
                name="unique_trainer_pokemon_fusion",
            )
        ]

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return f"Fusion of {self.trainer} + {self.pokemon} -> {self.result}"



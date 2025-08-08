"""Models related to Pokémon moves and movesets."""

from django.db import models
from django.core.exceptions import ValidationError


class Move(models.Model):
    """A normalized move entry."""

    name = models.CharField(max_length=50, unique=True)

    def __str__(self):  # pragma: no cover - simple repr
        return self.name


class PokemonLearnedMove(models.Model):
    """Through table linking a Pokémon to a learned move."""

    pokemon = models.ForeignKey(
        "OwnedPokemon",
        on_delete=models.CASCADE,
        db_index=True,
    )
    move = models.ForeignKey("Move", on_delete=models.CASCADE, db_index=True)

    class Meta:
        unique_together = ("pokemon", "move")
        indexes = [
            models.Index(
                fields=["pokemon"], name="pokemonlearnedmove_pokemon_idx"
            ),
            models.Index(fields=["move"], name="pokemonlearnedmove_move_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return f"{self.pokemon} knows {self.move}"


class Moveset(models.Model):
    """A set of up to four moves belonging to a Pokémon."""

    pokemon = models.ForeignKey(
        "OwnedPokemon", on_delete=models.CASCADE, related_name="movesets"
    )
    index = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["pokemon", "index"],
                name="unique_moveset_index",
            ),
            models.CheckConstraint(
                check=models.Q(index__gte=0, index__lte=3),
                name="moveset_index_range",
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return f"{self.pokemon} set {self.index}"

    def clean(self):
        """Validate moveset count per Pokémon."""
        super().clean()
        if self.pokemon and self.pokemon.movesets.exclude(pk=self.pk).count() >= 4:
            raise ValidationError("A Pokémon may only have four movesets.")


class MovesetSlot(models.Model):
    """A single move within a moveset."""

    moveset = models.ForeignKey(
        "Moveset", on_delete=models.CASCADE, related_name="slots"
    )
    move = models.ForeignKey("Move", on_delete=models.CASCADE)
    slot = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["moveset", "slot"],
                name="unique_moveset_slot",
            ),
            models.CheckConstraint(
                check=models.Q(slot__gte=1, slot__lte=4),
                name="movesetslot_slot_range",
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return f"{self.moveset} [{self.slot}] -> {self.move}"


class ActiveMoveslot(models.Model):
    """Mapping of active move slots for a Pokémon."""

    pokemon = models.ForeignKey("OwnedPokemon", on_delete=models.CASCADE, db_index=True)
    move = models.ForeignKey("Move", on_delete=models.CASCADE, db_index=True)
    slot = models.PositiveSmallIntegerField(db_index=True)
    current_pp = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ("pokemon", "slot")

    def __str__(self):  # pragma: no cover - simple repr
        return f"{self.pokemon} -> {self.move} [{self.slot}]"


class MovePPBoost(models.Model):
    """Store extra PP added to a move for a specific Pokémon."""

    pokemon = models.ForeignKey(
        "OwnedPokemon", on_delete=models.CASCADE, related_name="pp_boosts"
    )
    move = models.ForeignKey("Move", on_delete=models.CASCADE)
    bonus_pp = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = ("pokemon", "move")

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return f"{self.pokemon} {self.move} +{self.bonus_pp} PP"



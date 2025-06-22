"""Database models for Pokémon ownership."""

from evennia.objects.models import ObjectDB
from evennia.utils.idmapper.models import SharedMemoryModel
from django.db import models
import uuid


class Pokemon(models.Model):
    name = models.CharField(max_length=255)
    level = models.IntegerField()
    type_ = models.CharField(max_length=255)
    ability = models.CharField(max_length=50, blank=True)
    data = models.JSONField(default=dict, blank=True)
    trainer = models.ForeignKey(
        "Trainer",
        on_delete=models.CASCADE,
        related_name="owned_pokemon",
        null=True,
        blank=True,
    )

    def __str__(self):
        owner = f" owned by {self.trainer.user.key}" if self.trainer else ""
        return (
            f"{self.id}: {self.name} (Level {self.level}, Type: {self.type_}, "
            f"Ability: {self.ability})" + owner
        )


class UserStorage(models.Model):
    user = models.OneToOneField(ObjectDB, on_delete=models.CASCADE)
    active_pokemon = models.ManyToManyField(
        Pokemon, related_name="active_users"
    )
    stored_pokemon = models.ManyToManyField(
        Pokemon, related_name="stored_users", blank=True
    )


class StorageBox(models.Model):
    """A box of Pokémon stored for a particular user."""

    storage = models.ForeignKey(
        UserStorage, on_delete=models.CASCADE, related_name="boxes"
    )
    name = models.CharField(max_length=255)
    pokemon = models.ManyToManyField(Pokemon, related_name="boxes", blank=True)

    def __str__(self):
        return f"{self.name} (Owner: {self.storage.user.key})"


class OwnedPokemon(SharedMemoryModel):
    """Persistent data for a player's Pokémon."""

    unique_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    # Species & identity
    species = models.CharField(max_length=50)
    nickname = models.CharField(max_length=50, blank=True)
    nature = models.CharField(max_length=20)
    gender = models.CharField(max_length=10)
    shiny = models.BooleanField(default=False)
    level = models.IntegerField(default=1)
    experience = models.IntegerField(default=0)

    # Ownership & trainers
    original_trainer = models.ForeignKey(
        "typeclasses.characters.Character",
        related_name="original_pokemon",
        on_delete=models.CASCADE,
    )
    current_trainer = models.ForeignKey(
        "typeclasses.characters.Character",
        related_name="owned_pokemon",
        on_delete=models.CASCADE,
    )

    # Stats
    happiness = models.IntegerField(default=0)
    bond = models.IntegerField(default=0)
    ivs = models.JSONField(default=dict)
    evs = models.JSONField(default=dict)

    # Status
    current_hp = models.IntegerField(default=0)
    max_hp = models.IntegerField(default=0)
    status_condition = models.CharField(max_length=20, blank=True)
    walked_steps = models.IntegerField(default=0)

    # Battle context
    battle_id = models.IntegerField(null=True, blank=True)
    battle_team = models.CharField(max_length=1, blank=True)

    # Items & ability
    held_item = models.CharField(max_length=50, blank=True)
    ability = models.CharField(max_length=50)

    # Known moves and PP data
    known_moves = models.JSONField(default=list, blank=True)
    moveset = models.JSONField(default=list, blank=True)
    data = models.JSONField(default=dict, blank=True)


class ActiveMoveset(SharedMemoryModel):
    """Mapping of active move slots for a Pokémon."""

    pokemon = models.OneToOneField(
        OwnedPokemon,
        related_name="active_moveset",
        on_delete=models.CASCADE,
    )
    moves = models.JSONField(default=list, blank=True)


class GymBadge(models.Model):
    """A gym badge rewarded for defeating a particular gym."""

    name = models.CharField(max_length=255)
    region = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.region})"


class Trainer(models.Model):
    """Model storing trainer specific stats for a Character."""

    user = models.OneToOneField(
        ObjectDB, on_delete=models.CASCADE, related_name="trainer"
    )
    trainer_number = models.PositiveIntegerField(unique=True)
    money = models.PositiveIntegerField(default=0)
    seen_pokemon = models.ManyToManyField(
        Pokemon, related_name="seen_by_trainers", blank=True
    )
    badges = models.ManyToManyField(GymBadge, related_name="trainers", blank=True)

    def __str__(self):
        return f"Trainer {self.trainer_number} for {self.user.key}"

    # Helper methods
    def add_badge(self, badge: GymBadge) -> None:
        self.badges.add(badge)

    def add_money(self, amount: int) -> None:
        self.money += amount
        self.save()

    def log_seen_pokemon(self, pokemon: Pokemon) -> None:
        self.seen_pokemon.add(pokemon)

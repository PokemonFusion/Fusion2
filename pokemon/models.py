"""Database models for Pokémon ownership."""

from evennia import DefaultCharacter
from evennia.utils.idmapper.models import SharedMemoryModel
from django.db import models

class Pokemon(models.Model):
    name = models.CharField(max_length=255)
    level = models.IntegerField()
    type_ = models.CharField(max_length=255)
    ability = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return (
            f"{self.id}: {self.name} (Level {self.level}, Type: {self.type_}, "
            f"Ability: {self.ability})"
        )

class UserStorage(models.Model):
    user = models.OneToOneField(DefaultCharacter, on_delete=models.CASCADE)
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

    # Species & identity
    species = models.CharField(max_length=50)
    nickname = models.CharField(max_length=50, blank=True)
    nature = models.CharField(max_length=20)
    gender = models.CharField(max_length=10)
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
    ivs = models.CharField(max_length=32)
    ev_hp = models.IntegerField(default=0)
    ev_atk = models.IntegerField(default=0)
    ev_def = models.IntegerField(default=0)
    ev_spatk = models.IntegerField(default=0)
    ev_spdef = models.IntegerField(default=0)
    ev_speed = models.IntegerField(default=0)

    # Status
    current_hp = models.IntegerField(default=0)
    status_condition = models.CharField(max_length=20, blank=True)
    walked_steps = models.IntegerField(default=0)

    # Battle context
    battle_id = models.IntegerField(null=True, blank=True)
    battle_team = models.CharField(max_length=1, blank=True)

    # Items & ability
    holding_item = models.CharField(max_length=50, blank=True)
    ability = models.CharField(max_length=50)

    # Known moves and PP data
    known_moves = models.JSONField(default=dict, blank=True)


class ActiveMoveset(SharedMemoryModel):
    """Mapping of active move slots for a Pokémon."""

    pokemon = models.OneToOneField(
        OwnedPokemon,
        related_name="active_moveset",
        on_delete=models.CASCADE,
    )
    move_a = models.CharField(max_length=50, blank=True)
    move_b = models.CharField(max_length=50, blank=True)
    move_c = models.CharField(max_length=50, blank=True)
    move_d = models.CharField(max_length=50, blank=True)

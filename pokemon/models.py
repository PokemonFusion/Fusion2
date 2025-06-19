from evennia.objects.models import ObjectDB
from django.db import models

class Pokemon(models.Model):
    name = models.CharField(max_length=255)
    level = models.IntegerField()
    type_ = models.CharField(max_length=255)
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
            f"{self.id}: {self.name} (Level {self.level}, Type: {self.type_})" + owner
        )

class UserStorage(models.Model):
    user = models.OneToOneField(ObjectDB, on_delete=models.CASCADE)
    active_pokemon = models.ManyToManyField(Pokemon, related_name='active_users')
    stored_pokemon = models.ManyToManyField(Pokemon, related_name='stored_users')


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

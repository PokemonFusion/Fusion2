"""Trainer related models such as ``Trainer`` and inventory."""

from django.db import models
from evennia.objects.models import ObjectDB

from .core import SpeciesEntry


class GymBadge(models.Model):
    """A gym badge rewarded for defeating a particular gym."""

    name = models.CharField(max_length=255)
    region = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def __str__(self):  # pragma: no cover - simple repr
        return f"{self.name} ({self.region})"


class Trainer(models.Model):
    """Model storing trainer specific stats for a Character."""

    user = models.OneToOneField(
        ObjectDB, on_delete=models.CASCADE, related_name="trainer", db_index=True
    )
    trainer_number = models.PositiveIntegerField(unique=True)
    money = models.PositiveIntegerField(default=0)
    seen_pokemon = models.ManyToManyField(
        "SpeciesEntry", related_name="seen_by_trainers", blank=True
    )
    badges = models.ManyToManyField("GymBadge", related_name="trainers", blank=True)

    def __str__(self):  # pragma: no cover - simple repr
        return f"Trainer {self.trainer_number} for {self.user.key}"

    def add_badge(self, badge: GymBadge) -> None:
        self.badges.add(badge)

    def add_money(self, amount: int) -> None:
        self.money += amount
        self.save()

    def spend_money(self, amount: int) -> bool:
        """Remove money if available and return success."""
        if self.money < amount:
            return False
        self.money -= amount
        self.save()
        return True

    def log_seen_pokemon(self, species: str | int) -> None:
        """Record that the trainer has seen the given species."""
        if isinstance(species, int):
            entry = SpeciesEntry.objects.filter(pk=species).first()
        else:
            entry = SpeciesEntry.objects.filter(name__iexact=str(species)).first()
        if entry:
            self.seen_pokemon.add(entry)

    def add_item(self, item_name: str, amount: int = 1) -> None:
        """Add ``amount`` of ``item_name`` to this trainer's inventory."""
        item_name = item_name.lower()
        entry, _ = InventoryEntry.objects.get_or_create(
            owner=self, item_name=item_name, defaults={"quantity": 0}
        )
        entry.quantity += amount
        entry.save()

    def remove_item(self, item_name: str, amount: int = 1) -> bool:
        """Remove ``amount`` of ``item_name`` and return success."""
        item_name = item_name.lower()
        try:
            entry = InventoryEntry.objects.get(owner=self, item_name=item_name)
        except InventoryEntry.DoesNotExist:
            return False
        if entry.quantity < amount:
            return False
        entry.quantity -= amount
        if entry.quantity <= 0:
            entry.delete()
        else:
            entry.save()
        return True

    def list_inventory(self):
        """Return ``InventoryEntry`` objects owned by this trainer."""
        return InventoryEntry.objects.filter(owner=self).order_by("item_name")


class NPCTrainer(models.Model):
    """Static NPC trainer such as gym leaders."""

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):  # pragma: no cover - simple repr
        return self.name


class InventoryEntry(models.Model):
    """A quantity of a particular item owned by a trainer."""

    owner = models.ForeignKey(
        "Trainer", on_delete=models.CASCADE, related_name="inventory"
    )
    item_name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("owner", "item_name")

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return f"{self.item_name} x{self.quantity}"



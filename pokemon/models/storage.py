"""Storage related models for managing a trainer's Pokémon."""

from django.core.exceptions import ValidationError
from django.db import models
from evennia.objects.models import ObjectDB


class UserStorage(models.Model):
	user = models.OneToOneField(ObjectDB, on_delete=models.CASCADE, db_index=True)
	active_pokemon = models.ManyToManyField(
		"OwnedPokemon",
		related_name="active_users",
		through="ActivePokemonSlot",
	)
	stored_pokemon = models.ManyToManyField("OwnedPokemon", related_name="stored_users", blank=True)

	def add_active_pokemon(self, pokemon, slot: int | None = None) -> None:
		"""Add a Pokémon to the active party in the given slot."""
		existing = set(self.active_slots.values_list("slot", flat=True))
		if len(existing) >= 6:
			raise ValueError("Party already has six Pokémon.")
		if slot is None:
			for i in range(1, 7):
				if i not in existing:
					slot = i
					break
		if slot is None:
			raise ValueError("No available slot for Pokémon.")
		ActivePokemonSlot.objects.create(storage=self, pokemon=pokemon, slot=slot)

	def remove_active_pokemon(self, pokemon) -> None:
		"""Remove a Pokémon from the active party."""
		ActivePokemonSlot.objects.filter(storage=self, pokemon=pokemon).delete()

	def get_party(self):
		"""Return active Pokémon ordered by slot."""
		qs = self.active_pokemon.all()
		if hasattr(qs, "order_by"):
			qs = qs.order_by("active_slots__slot")
		return list(qs)


class StorageBox(models.Model):
	"""A box of Pokémon stored for a particular user."""

	storage = models.ForeignKey("UserStorage", on_delete=models.CASCADE, related_name="boxes", db_index=True)
	name = models.CharField(max_length=255)
	pokemon = models.ManyToManyField("OwnedPokemon", related_name="boxes", blank=True)

	def __str__(self):  # pragma: no cover - simple repr
		return f"{self.name} (Owner: {self.storage.user.key})"


def ensure_boxes(storage: "UserStorage", count: int = 8) -> "UserStorage":
	"""Ensure that a storage container has at least ``count`` boxes."""

	existing = storage.boxes.count()
	for i in range(existing + 1, count + 1):
		StorageBox.objects.create(storage=storage, name=f"Box {i}")
	return storage


class ActivePokemonSlot(models.Model):
	"""Mapping of active Pokémon party slots."""

	storage = models.ForeignKey("UserStorage", on_delete=models.CASCADE, related_name="active_slots", db_index=True)
	pokemon = models.ForeignKey("OwnedPokemon", on_delete=models.CASCADE, related_name="active_slots", db_index=True)
	slot = models.PositiveSmallIntegerField(db_index=True)

	class Meta:
		unique_together = (
			("storage", "slot"),
			("storage", "pokemon"),
		)

	def clean(self):
		if self.slot < 1 or self.slot > 6:
			raise ValidationError("Slot must be between 1 and 6.")
		count = ActivePokemonSlot.objects.filter(storage=self.storage).exclude(pk=self.pk).count()
		if count >= 6 and not ActivePokemonSlot.objects.filter(pk=self.pk).exists():
			raise ValidationError("Party already has six Pokémon.")

	def save(self, *args, **kwargs):
		self.full_clean()
		return super().save(*args, **kwargs)

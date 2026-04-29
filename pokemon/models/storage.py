"""Storage related models for managing a trainer's Pokemon."""

from django.core.exceptions import ValidationError
from django.db import models, transaction
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
		"""Add a Pokemon to the active party in the given slot."""
		existing = set(
			self.placements.filter(location_type=PokemonPlacement.LocationType.PARTY).values_list("slot", flat=True)
		)
		if len(existing) >= 6:
			raise ValueError("Party already has six Pokemon.")
		if slot is None:
			for i in range(1, 7):
				if i not in existing:
					slot = i
					break
		if slot is None:
			raise ValueError("No available slot for Pokemon.")
		with transaction.atomic():
			PokemonPlacement.objects.update_or_create(
				pokemon=pokemon,
				defaults={
					"storage": self,
					"location_type": PokemonPlacement.LocationType.PARTY,
					"slot": slot,
					"box": None,
					"box_position": None,
				},
			)
			_sync_legacy_storage_relations(self, pokemon)

	def remove_active_pokemon(self, pokemon) -> None:
		"""Remove a Pokemon from the active party."""
		with transaction.atomic():
			self.placements.filter(
				storage=self,
				pokemon=pokemon,
				location_type=PokemonPlacement.LocationType.PARTY,
			).delete()
			_sync_legacy_storage_relations(self, pokemon)

	def get_party(self):
		"""Return active Pokemon ordered by slot."""
		placements = list(
			self.placements.filter(location_type=PokemonPlacement.LocationType.PARTY)
			.select_related("pokemon")
			.order_by("slot", "id")
		)
		if placements:
			return [placement.pokemon for placement in placements]
		qs = self.active_pokemon.all()
		if hasattr(qs, "order_by"):
			qs = qs.order_by("active_slots__slot")
		return list(qs)

	def get_stored_pokemon(self):
		"""Return boxed Pokemon ordered by box and position."""
		placements = list(
			self.placements.filter(location_type=PokemonPlacement.LocationType.BOX)
			.select_related("pokemon", "box")
			.order_by("box_id", "box_position", "id")
		)
		if placements:
			return [placement.pokemon for placement in placements]
		return list(self.stored_pokemon.all())

	def has_party_pokemon(self) -> bool:
		return bool(self.get_party())

	def active_pokemon_count(self) -> int:
		return len(self.get_party())

	def sync_legacy_relations(self) -> None:
		for placement in self.placements.select_related("pokemon"):
			_sync_legacy_storage_relations(self, placement.pokemon)


class StorageBox(models.Model):
	"""A box of Pokemon stored for a particular user."""

	storage = models.ForeignKey("UserStorage", on_delete=models.CASCADE, related_name="boxes", db_index=True)
	name = models.CharField(max_length=255)
	pokemon = models.ManyToManyField("OwnedPokemon", related_name="boxes", blank=True)

	def __str__(self):  # pragma: no cover - simple repr
		return f"{self.name} (Owner: {self.storage.user.key})"

	def get_pokemon(self):
		placements = list(self.placements.select_related("pokemon").order_by("box_position", "id"))
		if placements:
			return [placement.pokemon for placement in placements]
		return list(self.pokemon.all())


class PokemonPlacement(models.Model):
	"""Canonical location for a trainer-owned Pokemon."""

	class LocationType(models.TextChoices):
		PARTY = "party", "Party"
		BOX = "box", "Box"

	storage = models.ForeignKey("UserStorage", on_delete=models.CASCADE, related_name="placements", db_index=True)
	pokemon = models.OneToOneField("OwnedPokemon", on_delete=models.CASCADE, related_name="placement", db_index=True)
	location_type = models.CharField(max_length=10, choices=LocationType.choices, db_index=True)
	slot = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)
	box = models.ForeignKey(
		"StorageBox",
		on_delete=models.CASCADE,
		related_name="placements",
		null=True,
		blank=True,
		db_index=True,
	)
	box_position = models.PositiveIntegerField(null=True, blank=True, db_index=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(
				fields=("storage", "slot"),
				condition=models.Q(location_type="party"),
				name="pokemon_party_slot_unique",
			),
		]

	def clean(self):
		if self.location_type == self.LocationType.PARTY:
			if self.slot is None or self.slot < 1 or self.slot > 6:
				raise ValidationError("Party slot must be between 1 and 6.")
			if self.box_id is not None or self.box_position is not None:
				raise ValidationError("Party Pokemon cannot have box placement data.")
		elif self.location_type == self.LocationType.BOX:
			if self.box_id is None:
				raise ValidationError("Box placement requires a storage box.")
			if self.box and self.box.storage_id != self.storage_id:
				raise ValidationError("Box does not belong to this storage.")
			self.slot = None

	def save(self, *args, **kwargs):
		self.full_clean()
		result = super().save(*args, **kwargs)
		_sync_legacy_storage_relations(self.storage, self.pokemon)
		return result

	def delete(self, *args, **kwargs):
		storage = self.storage
		pokemon = self.pokemon
		result = super().delete(*args, **kwargs)
		_sync_legacy_storage_relations(storage, pokemon)
		return result


def _sync_legacy_storage_relations(storage: "UserStorage", pokemon) -> None:
	"""Mirror canonical placement into legacy relations during cutover."""

	placement = storage.placements.filter(pokemon=pokemon).select_related("box").first()
	storage.stored_pokemon.remove(pokemon)
	pokemon.boxes.clear()
	ActivePokemonSlot.objects.filter(storage=storage, pokemon=pokemon).delete()

	if placement is None:
		return

	if placement.location_type == PokemonPlacement.LocationType.PARTY:
		if placement.slot is not None:
			ActivePokemonSlot.objects.update_or_create(
				storage=storage,
				pokemon=pokemon,
				defaults={"slot": placement.slot},
			)
	elif placement.location_type == PokemonPlacement.LocationType.BOX:
		storage.stored_pokemon.add(pokemon)
		if placement.box is not None:
			placement.box.pokemon.add(pokemon)


def ensure_boxes(storage: "UserStorage", count: int = 8) -> "UserStorage":
	"""Ensure that a storage container has at least ``count`` boxes."""

	existing = storage.boxes.count()
	for i in range(existing + 1, count + 1):
		StorageBox.objects.create(storage=storage, name=f"Box {i}")
	return storage


def assign_to_first_storage_box(storage: "UserStorage", mon) -> "StorageBox":
	"""Return the default box to use for ``mon`` within ``storage``."""

	ensure_boxes(storage)
	boxes = storage.boxes.all().order_by("id")
	box = boxes.first() if hasattr(boxes, "first") else next(iter(boxes), None)
	if box is None:
		raise ValueError("Storage has no available boxes.")
	return box


class ActivePokemonSlot(models.Model):
	"""Mapping of active Pokemon party slots."""

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
			raise ValidationError("Party already has six Pokemon.")

	def save(self, *args, **kwargs):
		self.full_clean()
		return super().save(*args, **kwargs)


def move_to_party(mon, storage: UserStorage, slot: int | None = None) -> None:
	"""Move ``mon`` into ``storage``'s active party."""

	with transaction.atomic():
		storage.placements.filter(pokemon=mon).delete()
		storage.add_active_pokemon(mon, slot)


def move_to_box(mon, storage: UserStorage, box: StorageBox | None = None) -> StorageBox:
	"""Place ``mon`` into ``box`` within ``storage``."""

	if box is None:
		box = assign_to_first_storage_box(storage, mon)
	if box.storage != storage:
		raise ValueError("Box does not belong to storage.")
	with transaction.atomic():
		next_pos = (box.placements.aggregate(models.Max("box_position")).get("box_position__max") or 0) + 1
		PokemonPlacement.objects.update_or_create(
			pokemon=mon,
			defaults={
				"storage": storage,
				"location_type": PokemonPlacement.LocationType.BOX,
				"slot": None,
				"box": box,
				"box_position": next_pos,
			},
		)
	return box


def release(mon, storage: UserStorage) -> None:
	"""Release ``mon`` from ``storage`` entirely."""

	with transaction.atomic():
		storage.placements.filter(pokemon=mon).delete()
		_sync_legacy_storage_relations(storage, mon)
		mon.delete()

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
		"""Place a Pokemon through the canonical transition service."""
		move_to_party(pokemon, self, slot)

	def remove_active_pokemon(self, pokemon) -> None:
		"""Deposit a Pokemon instead of leaving an owned row unplaced."""
		move_to_box(pokemon, self)

	def reserve_for_fusion(self, pokemon):
		"""Keep an explicit placement for a Pokemon used as a fusion form."""
		from pokemon.services.placement import PlacementService
		return PlacementService(self).reserve_for_fusion(pokemon)

	def return_from_fusion(self, pokemon, preferred_slot=None):
		"""Return a temporary fusion through the canonical transition service."""
		from pokemon.services.placement import PlacementService
		return PlacementService(self).return_from_fusion(pokemon, preferred_slot)

	def get_party(self):
		"""Return active Pokemon ordered by slot."""
		placements = list(
			self.placements.filter(location_type=PokemonPlacement.LocationType.PARTY)
			.select_related("pokemon")
			.order_by("slot", "id")
		)
		return [placement.pokemon for placement in placements]

	def get_stored_pokemon(self):
		"""Return boxed Pokemon ordered by box and position."""
		placements = list(
			self.placements.filter(location_type=PokemonPlacement.LocationType.BOX)
			.select_related("pokemon", "box")
			.order_by("box_id", "box_position", "id")
		)
		return [placement.pokemon for placement in placements]

	def has_party_pokemon(self) -> bool:
		return bool(self.get_party())

	def active_pokemon_count(self) -> int:
		return len(self.get_party())

	def sync_legacy_relations(self) -> None:
		"""Rebuild mirrors from valid canonical rows while excluding other writers."""
		from pokemon.services.placement import PlacementService
		with PlacementService(self).locked() as storage:
			for placement in storage.placements.select_related("pokemon"):
				placement.full_clean()
				_sync_legacy_storage_relations(storage, placement.pokemon)


class StorageBox(models.Model):
	"""A box of Pokemon stored for a particular user."""

	storage = models.ForeignKey("UserStorage", on_delete=models.CASCADE, related_name="boxes", db_index=True)
	name = models.CharField(max_length=255)
	pokemon = models.ManyToManyField("OwnedPokemon", related_name="boxes", blank=True)

	def __str__(self):  # pragma: no cover - simple repr
		return f"{self.name} (Owner: {self.storage.user.key})"

	def get_pokemon(self):
		placements = list(self.placements.select_related("pokemon").order_by("box_position", "id"))
		return [placement.pokemon for placement in placements]


class PokemonPlacement(models.Model):
	"""Canonical location for a trainer-owned Pokemon."""

	class LocationType(models.TextChoices):
		PARTY = "party", "Party"
		BOX = "box", "Box"
		FUSION = "fusion", "Fusion reservation"

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
			models.UniqueConstraint(
				fields=("box", "box_position"), condition=models.Q(location_type="box"),
				name="pokemon_box_position_unique",
			),
			models.CheckConstraint(
				condition=(
					models.Q(location_type="party", slot__isnull=False, slot__gte=1, slot__lte=6,
						box__isnull=True, box_position__isnull=True)
					| models.Q(location_type="box", slot__isnull=True, box__isnull=False,
						box_position__isnull=False, box_position__gte=1)
					| models.Q(location_type="fusion", slot__isnull=True, box__isnull=True,
						box_position__isnull=True)
				), name="pokemon_placement_shape",
			),
		]

	def clean(self):
		"""Validate cross-table ownership as well as location shape."""
		if not self.pokemon.trainer_id or self.pokemon.trainer.user_id != self.storage.user_id:
			raise ValidationError("Pokemon owner does not match placement storage.")
		if self.location_type == self.LocationType.PARTY:
			if self.slot is None or self.slot < 1 or self.slot > 6:
				raise ValidationError("Party slot must be between 1 and 6.")
			if self.box_id is not None or self.box_position is not None:
				raise ValidationError("Party Pokemon cannot have box placement data.")
		elif self.location_type == self.LocationType.BOX:
			if self.box_id is None or self.box_position is None or self.box_position < 1 or self.slot is not None:
				raise ValidationError("Box placement requires a box, positive position, and no party slot.")
			if self.box.storage_id != self.storage_id:
				raise ValidationError("Box does not belong to this storage.")
		elif self.location_type == self.LocationType.FUSION:
			if self.slot is not None or self.box_id is not None or self.box_position is not None:
				raise ValidationError("Fusion reservations cannot have party or box data.")
		else:
			raise ValidationError("Unknown placement state.")

	def save(self, *args, **kwargs):
		"""Keep canonical data and legacy mirrors in one transaction."""
		with transaction.atomic():
			self.full_clean()
			result = super().save(*args, **kwargs)
			_sync_legacy_storage_relations(self.storage, self.pokemon)
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

	with transaction.atomic():
		UserStorage.objects.select_for_update().get(pk=storage.pk)
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
	"""Move ``mon`` into its owner's party using a serialized transition."""
	from pokemon.services.placement import PlacementService
	PlacementService(storage).to_party(mon, slot)


def move_to_box(mon, storage: UserStorage, box: StorageBox | None = None) -> StorageBox:
	"""Deposit ``mon`` through the canonical transition service."""
	from pokemon.services.placement import PlacementService
	return PlacementService(storage).to_box(mon, box)


def release(mon, storage: UserStorage) -> None:
	"""Release an owned Pokemon through the canonical transition service."""
	from pokemon.services.placement import PlacementService
	PlacementService(storage).release(mon)


class CaptureReceipt(models.Model):
	"""Durable encounter claim, retained even after the captured Pokemon is released."""

	encounter_id = models.UUIDField(primary_key=True, editable=False)
	storage = models.ForeignKey(UserStorage, on_delete=models.CASCADE)
	pokemon = models.OneToOneField("OwnedPokemon", null=True, on_delete=models.SET_NULL)
	owned_id = models.UUIDField(editable=False)
	location = models.CharField(max_length=10)
	party_slot = models.PositiveSmallIntegerField(null=True)
	box_name = models.CharField(max_length=255, null=True)
	created_at = models.DateTimeField(auto_now_add=True)

"""Canonical ownership and placement transitions.

All writers lock storage first, then freshly load the Pokemon under a row lock.
The storage lock serializes capacity checks even when the party/box is empty.
Locks are held by the outermost transaction, including compound swaps/capture.
"""

from contextlib import contextmanager

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max


class PlacementError(ValueError):
    """A transition would violate ownership or canonical placement."""


class PlacementService:
    """Move owned Pokemon without an intermediate committed unplaced state."""

    def __init__(self, storage):
        self.storage_id = storage.pk

    @contextmanager
    def locked(self):
        """Serialize all placement writers for one character's storage."""
        from pokemon.models.storage import UserStorage

        with transaction.atomic():
            storage = UserStorage.objects.select_for_update().get(pk=self.storage_id)
            storage.refresh_from_db()
            yield storage

    def _pokemon(self, mon, storage):
        """Lock and validate persisted ownership, never a cached trainer value."""
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.storage import PokemonPlacement

        pokemon = OwnedPokemon.objects.select_for_update().get(pk=mon.pk)
        pokemon.refresh_from_db()
        if not pokemon.trainer_id or pokemon.trainer.user_id != storage.user_id:
            raise PlacementError("Pokemon does not belong to this storage's trainer.")
        placement = PokemonPlacement.objects.filter(pokemon=pokemon).first()
        if placement:
            if placement.storage_id != storage.pk:
                raise PlacementError("Conflicting placement owner; staff review is required.")
            try:
                placement.full_clean()
            except ValidationError as error:
                raise PlacementError(f"Invalid placement; staff review is required: {error}") from error
        # Do not silently erase evidence of legacy ownership conflicts.
        if (pokemon.active_users.exclude(pk=storage.pk).exists()
                or pokemon.stored_users.exclude(pk=storage.pk).exists()
                or pokemon.boxes.exclude(storage=storage).exists()):
            raise PlacementError("Conflicting legacy membership; staff review is required.")
        active = set(pokemon.active_slots.values_list("storage_id", "slot"))
        stored = set(pokemon.stored_users.values_list("pk", flat=True))
        boxed = set(pokemon.boxes.values_list("pk", flat=True))
        expected = (set(), set(), set())
        if placement and placement.location_type == "party":
            expected = ({(storage.pk, placement.slot)}, set(), set())
        elif placement and placement.location_type == "box":
            expected = (set(), {storage.pk}, {placement.box_id})
        if (active, stored, boxed) != expected:
            raise PlacementError("Conflicting legacy membership; staff review is required.")
        return pokemon, placement

    def _write(self, pokemon, storage, current, location, *, slot=None, box=None, position=None):
        """Update the single canonical row and its compatibility mirrors atomically."""
        from pokemon.models.storage import PokemonPlacement

        placement = current or PokemonPlacement(pokemon=pokemon, storage=storage)
        placement.location_type = location
        placement.slot = slot
        placement.box = box
        placement.box_position = position
        placement.save()
        return placement

    def _party(self, pokemon, storage, current, slot=None, *, allow_fusion=False):
        """Allocate or retain a slot while holding the storage lock."""
        self._check_reservation(current, allow_fusion)
        if slot is not None and (isinstance(slot, bool) or slot not in range(1, 7)):
            raise PlacementError("Party slot must be between 1 and 6.")
        if current and current.location_type == "party" and (slot is None or slot == current.slot):
            return current
        occupied = set(storage.placements.filter(location_type="party").exclude(
            pokemon=pokemon).values_list("slot", flat=True))
        if slot is None:
            slot = next((value for value in range(1, 7) if value not in occupied), None)
        if slot is None:
            raise PlacementError("Party already has six Pokemon.")
        if slot in occupied:
            raise PlacementError("Party slot is already occupied.")
        return self._write(pokemon, storage, current, "party", slot=slot)

    @staticmethod
    def _check_reservation(current, allow_fusion):
        """Only the fusion return path may consume a fusion reservation."""
        if current and current.location_type == "fusion" and not allow_fusion:
            raise PlacementError("Pokemon is reserved for fusion.")

    def _box(self, pokemon, storage, current, box=None, *, allow_fusion=False):
        """Allocate a unique positive box position, preserving successful retries."""
        from pokemon.models.storage import StorageBox, assign_to_first_storage_box

        self._check_reservation(current, allow_fusion)
        if box is None and current and current.location_type == "box":
            return current
        if box is None:
            box = assign_to_first_storage_box(storage, pokemon)
        box = StorageBox.objects.get(pk=box.pk)
        if box.storage_id != storage.pk:
            raise PlacementError("Box does not belong to this storage.")
        if current and current.location_type == "box" and current.box_id == box.pk:
            return current
        position = (box.placements.aggregate(value=Max("box_position"))["value"] or 0) + 1
        return self._write(pokemon, storage, current, "box", box=box, position=position)

    def to_party(self, mon, slot=None):
        """Idempotently place a Pokemon in the party or reject capacity/conflict."""
        with self.locked() as storage:
            pokemon, current = self._pokemon(mon, storage)
            return self._party(pokemon, storage, current, slot)

    def to_box(self, mon, box=None):
        """Idempotently deposit a Pokemon into a box belonging to its owner."""
        with self.locked() as storage:
            pokemon, current = self._pokemon(mon, storage)
            return self._box(pokemon, storage, current, box).box

    def place_new(self, mon):
        """Place a newly created Pokemon, spilling a full party into storage."""
        with self.locked() as storage:
            pokemon, current = self._pokemon(mon, storage)
            if current:
                return current
            if storage.placements.filter(location_type="party").count() < 6:
                return self._party(pokemon, storage, current)
            return self._box(pokemon, storage, current)

    def reserve_for_fusion(self, mon):
        """Retain ownership while an existing fusion form is outside party/boxes."""
        with self.locked() as storage:
            pokemon, current = self._pokemon(mon, storage)
            if current is None:
                raise PlacementError("Pokemon has no placement; staff review is required.")
            if current.location_type == "fusion":
                return current
            return self._write(pokemon, storage, current, "fusion")

    def return_from_fusion(self, mon, preferred_slot=None):
        """Return a temporary fusion to a free party slot, otherwise to a box."""
        with self.locked() as storage:
            pokemon, current = self._pokemon(mon, storage)
            if current is None:
                raise PlacementError("Pokemon has no placement; staff review is required.")
            if current.location_type != "fusion":
                return current
            occupied = set(storage.placements.filter(location_type="party").values_list("slot", flat=True))
            if len(occupied) < 6:
                slot = preferred_slot if preferred_slot in range(1, 7) and preferred_slot not in occupied else None
                return self._party(pokemon, storage, current, slot, allow_fusion=True)
            return self._box(pokemon, storage, current, allow_fusion=True)

    def swap(self, mon, slot, box):
        """Read the outgoing member after locking, then atomically swap both rows."""
        from pokemon.models.storage import PokemonPlacement

        with self.locked() as storage:
            pokemon, current = self._pokemon(mon, storage)
            if current and current.location_type == "party" and current.slot == slot:
                return None
            if current is None or current.location_type != "box" or current.box_id != box.pk:
                raise PlacementError("Pokemon is not in that box.")
            if slot not in range(1, 7):
                raise PlacementError("Party slot must be between 1 and 6.")
            outgoing = PokemonPlacement.objects.filter(storage=storage, location_type="party", slot=slot).first()
            previous = None
            if outgoing:
                previous, previous_placement = self._pokemon(outgoing.pokemon, storage)
                self._box(previous, storage, previous_placement, box)
            self._party(pokemon, storage, current, slot)
            return previous

    def release(self, mon):
        """Delete an owned Pokemon only after verifying its owner and reservation."""
        from pokemon.models.core import OwnedPokemon

        with self.locked() as storage:
            if not OwnedPokemon.objects.filter(pk=mon.pk).exists():
                return
            pokemon, current = self._pokemon(mon, storage)
            self._check_reservation(current, False)
            pokemon.delete()

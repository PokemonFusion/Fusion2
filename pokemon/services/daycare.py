"""Atomic paid Daycare custody over canonical placement and shared reservations."""

from uuid import UUID

from django.utils import timezone

from pokemon.services.ownership import (
    OwnershipError, PokemonReservations, acting_character, assert_transferable,
    assert_character_free, fresh_owned, locked_owners,
)
from pokemon.services.placement import PlacementService
from pokemon.services.trading import TradeOffers


class Daycare:
    """Keep two existing assets without healing, passive EXP or implicit breeding."""

    capacity = 2
    deposit_fee = 100

    def __init__(self, actor, *, clock=None):
        """Use one real character's trainer, storage and custody receipts."""
        self.actor = acting_character(actor)
        self.actor_id = self.actor.pk
        self.clock = clock or timezone.now

    @staticmethod
    def identifier(value):
        """Require an unambiguous persisted entry identity for retrieval."""
        try:
            return UUID(str(value))
        except (TypeError, ValueError) as error:
            raise OwnershipError("Use the full entry ID from +daycare.") from error

    def deposit(self, selector):
        """Charge once and remove party/box availability in the same transaction."""
        from pokemon.models.daycare import DaycareEntry
        from pokemon.models.trainer import Trainer

        with locked_owners((self.actor_id,)) as (characters, storages, trainers):
            identifier = TradeOffers.select(self.actor_id, selector)
            storage, trainer = storages[self.actor_id], trainers[self.actor_id]
            existing = DaycareEntry.objects.select_for_update().filter(storage=storage, owned_id=identifier, state="active").first()
            if existing:
                return existing
            source, placement = PlacementService(storage)._pokemon(fresh_owned(identifier, lock=True), storage)
            assert_transferable(characters[self.actor_id], source, placement)
            if source.is_egg:
                raise OwnershipError("Eggs cannot be deposited as Daycare parents.")
            occupied = set(DaycareEntry.objects.filter(storage=storage, state="active").values_list("place", flat=True))
            place = next((value for value in range(1, self.capacity + 1) if value not in occupied), None)
            if place is None:
                raise OwnershipError("Your Daycare already holds two Pokemon. Retrieve one first.")
            if trainer.money < self.deposit_fee:
                raise OwnershipError("Daycare deposit costs 100 trainer money; retrieval is free.")
            entry = DaycareEntry.objects.create(storage=storage, pokemon=source, owned_id=source.pk,
                saved_name=source.name, place=place, fee=self.deposit_fee, preferred_party_slot=placement.slot)
            PokemonReservations(self.actor).claim("daycare", [source.pk], entry.pk)
            PlacementService(storage)._write(source, storage, placement, "daycare")
            Trainer.objects.filter(pk=trainer.pk).update(money=trainer.money - self.deposit_fee)
            return entry

    def retrieve(self, entry_id):
        """Return the exact asset once, with party-to-box overflow and no new fee."""
        from pokemon.models.daycare import DaycareEntry
        from pokemon.models.ownership import PokemonReservation

        entry_id = self.identifier(entry_id)
        with locked_owners((self.actor_id,)) as (characters, storages, _):
            storage = storages[self.actor_id]
            entry = DaycareEntry.objects.select_for_update().filter(pk=entry_id, storage=storage).first()
            if entry is None:
                raise OwnershipError("That Daycare entry does not belong to this character.")
            if entry.state == "retrieved":
                return entry.receipt
            assert_character_free(characters[self.actor_id])
            # Breeding adds a persistent active-cycle reference in its own cohort.
            if getattr(entry, "active_cycle_id", None):
                raise OwnershipError("Collect or cancel the active breeding cycle before retrieving its parents.")
            source, placement = PlacementService(storage)._pokemon(fresh_owned(entry.owned_id, lock=True), storage,
                                                                   reservation_token=entry.pk)
            claim = PokemonReservation.objects.filter(pokemon=source, storage=storage, kind="daycare", token=entry.pk).first()
            if placement is None or placement.location_type != "daycare" or claim is None:
                raise OwnershipError("This Daycare entry needs staff inspection; no fee or Pokemon changed.")
            claim.delete()
            occupied = set(storage.placements.filter(location_type="party").values_list("slot", flat=True))
            service = PlacementService(storage)
            if len(occupied) < 6:
                preferred = entry.preferred_party_slot if entry.preferred_party_slot not in occupied else None
                destination = service._party(source, storage, placement, preferred, allow_daycare=True)
            else:
                destination = service._box(source, storage, placement, allow_daycare=True)
            entry.state, entry.retrieved_at = "retrieved", self.clock()
            entry.receipt = {"entry": str(entry.pk), "pokemon": str(source.pk), "owner": self.actor_id,
                "location": destination.location_type, "slot": destination.slot,
                "box": destination.box_id, "position": destination.box_position, "retrieval_fee": 0}
            entry.save(update_fields=["state", "retrieved_at", "receipt"])
            return entry.receipt

    def entries(self):
        """Read active and recent own outcomes without creating any trainer assets."""
        from django.db.models import Case, Value, When
        from pokemon.models.daycare import DaycareEntry

        return list(DaycareEntry.objects.filter(storage__user_id=self.actor_id).order_by(
            Case(When(state="active", then=Value(0)), default=Value(1)), "-deposited_at")[:30])

    @staticmethod
    def describe(entry):
        """Keep the stable custody and Pokemon identities visible after reconnect."""
        name = entry.saved_name
        breeding = (f" Active breeding cycle: {entry.active_cycle_id}; use +breed to collect/cancel before retrieval."
                    if entry.active_cycle_id else "")
        return (f"Daycare {entry.pk}: {entry.state}; place {entry.place}; {name} [{entry.owned_id}]. "
                f"Deposit fee paid: {entry.fee}; retrieval free. No passive EXP or healing. "
                f"Use +daycare retrieve {entry.pk}." + breeding + (f" Receipt: {entry.receipt}" if entry.receipt else ""))

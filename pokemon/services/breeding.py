"""One paid breeding outcome, canonical egg collection and current-owner hatching."""

from contextlib import contextmanager
from datetime import timedelta
import random
import secrets
from uuid import UUID, uuid4

from django.db import transaction
from django.db.models import Max, Q
from django.utils import timezone

from pokemon.names import normalize_name
from pokemon.services.breeding_rules import BreedingRuleError, BreedingRules
from pokemon.services.ownership import (
    OwnershipError, acting_character, assert_character_free, fresh_owned, locked_owners,
)
from pokemon.services.placement import PlacementService


class Breeding:
    """Use explicit wall-clock policy; status and retries never advance production."""

    fee = 500
    production_time = timedelta(minutes=30)
    parent_cooldown = timedelta(hours=24)
    hatch_time = timedelta(minutes=20)

    def __init__(self, actor, *, clock=None, rng=None):
        """Bind authority to an actual character; controllable clocks/RNG are test seams."""
        self.actor = acting_character(actor)
        self.actor_id = self.actor.pk
        self.clock = clock or timezone.now
        self.rng = rng or random.Random(secrets.randbits(256))

    @staticmethod
    def identifier(value):
        """Use exact persisted cycle or egg identities without a foreign fallback."""
        try:
            return UUID(str(value))
        except (TypeError, ValueError) as error:
            raise OwnershipError("Use the full cycle/egg ID from +breed.") from error

    @staticmethod
    def _parents(storage, *, cycle_id=None):
        """Lock both existing Daycare entries and check their exact custody claims."""
        from pokemon.models.daycare import DaycareEntry
        from pokemon.models.ownership import PokemonReservation

        entries = list(DaycareEntry.objects.select_for_update().filter(storage=storage, state="active").order_by("place", "pk"))
        if len(entries) != 2:
            raise OwnershipError("Deposit two eligible Pokemon in your Daycare first; use +breed check.")
        sources = []
        for entry in entries:
            if cycle_id is not None and entry.active_cycle_id != cycle_id:
                raise OwnershipError("The recorded parent/cycle link needs staff inspection.")
            if entry.active_cycle_id and entry.active_cycle_id != cycle_id:
                raise OwnershipError("These parents already belong to an active breeding cycle.")
            source, placement = PlacementService(storage)._pokemon(fresh_owned(entry.owned_id, lock=True), storage,
                                                                   reservation_token=entry.pk)
            if (placement is None or placement.location_type != "daycare"
                    or not PokemonReservation.objects.filter(pokemon=source, storage=storage, kind="daycare", token=entry.pk).exists()):
                raise OwnershipError("Parent custody needs staff inspection; no breeding fee was charged.")
            sources.append(source)
        return entries, sources

    @staticmethod
    def _cooldown(sources):
        """Read scalar parent UUID history, including cancelled and previous-owner cycles."""
        from pokemon.models.breeding import BreedingCycle

        ids = [source.pk for source in sources]
        return BreedingCycle.objects.filter(Q(parent_a_uuid__in=ids) | Q(parent_b_uuid__in=ids)).aggregate(
            value=Max("next_ready_at"))["value"]

    def check(self):
        """Validate ordinary pair eligibility without choosing random traits or charging."""
        with locked_owners((self.actor_id,)) as (characters, storages, _):
            assert_character_free(characters[self.actor_id])
            _, sources = self._parents(storages[self.actor_id])
            try:
                child, _, _ = BreedingRules.pair(*sources)
            except BreedingRuleError as error:
                raise OwnershipError(str(error)) from error
            until = self._cooldown(sources)
            return {"offspring": child.name, "cooldown_until": until,
                    "ready_to_start": until is None or until <= self.clock()}

    def start(self):
        """Seal traits, egg UUID, parent references, cooldown and one debit together."""
        from pokemon.models.breeding import BreedingCycle
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.models.trainer import Trainer

        with locked_owners((self.actor_id,)) as (characters, storages, trainers):
            storage, trainer = storages[self.actor_id], trainers[self.actor_id]
            existing = BreedingCycle.objects.select_for_update().filter(storage=storage, state="producing").first()
            if existing:
                self._parents(storage, cycle_id=existing.pk)
                return existing
            assert_character_free(characters[self.actor_id])
            entries, sources = self._parents(storage)
            until = self._cooldown(sources)
            if until is not None and until > self.clock():
                raise OwnershipError(f"One of these parents is cooling down until {until.isoformat()}.")
            if trainer.money < self.fee:
                raise OwnershipError("A breeding cycle costs 500 trainer money. No cycle or charge was created.")
            moves = [list(ActiveMoveslot.objects.filter(pokemon=source).order_by("slot").values_list("move__name", flat=True))
                     for source in sources]
            try:
                plan = BreedingRules.plan(*sources, moves, rng=self.rng)
            except BreedingRuleError as error:
                raise OwnershipError(str(error)) from error
            now = self.clock()
            cycle = BreedingCycle.objects.create(storage=storage, origin_character_id=self.actor_id,
                parent_a=entries[0], parent_b=entries[1], parent_a_uuid=sources[0].pk, parent_b_uuid=sources[1].pk,
                egg_uuid=uuid4(), plan=plan, fee=self.fee, started_at=now,
                ready_at=now + self.production_time, next_ready_at=now + self.parent_cooldown)
            for entry in entries:
                entry.active_cycle = cycle
                entry.save(update_fields=["active_cycle"])
            Trainer.objects.filter(pk=trainer.pk).update(money=trainer.money - self.fee)
            return cycle

    @contextmanager
    def locked_cycle(self, cycle_id):
        """Take the owning character/storage before its exact durable cycle."""
        from pokemon.models.breeding import BreedingCycle

        identifier = self.identifier(cycle_id)
        with locked_owners((self.actor_id,)) as owners:
            cycle = BreedingCycle.objects.select_for_update().filter(pk=identifier, origin_character_id=self.actor_id).first()
            if cycle is None:
                raise OwnershipError("That breeding cycle does not belong to this character.")
            yield cycle, owners

    @staticmethod
    def _release_parents(cycle):
        """Clear only this completed/cancelled cycle's entry references."""
        from pokemon.models.daycare import DaycareEntry

        return DaycareEntry.objects.filter(active_cycle=cycle).update(active_cycle=None)

    def cancel(self, cycle_id):
        """Keep the paid outcome/cooldown while deliberately ending uncollected production."""
        with self.locked_cycle(cycle_id) as (cycle, _):
            if cycle.state == "collected":
                raise OwnershipError(f"This cycle already delivered egg {cycle.egg_uuid}; collection is not refundable.")
            if cycle.state == "producing":
                self._release_parents(cycle)
                cycle.state, cycle.closed_at = "cancelled", self.clock()
                cycle.receipt = {"cycle": str(cycle.pk), "state": "cancelled", "closed_by": self.actor_id,
                    "planned_egg": str(cycle.egg_uuid), "refund": 0, "cooldown_until": cycle.next_ready_at.isoformat()}
                cycle.save(update_fields=["state", "closed_at", "receipt"])
            return cycle.receipt

    def collect(self, cycle_id):
        """Create the predetermined owned UUID once through the normal placement helper."""
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.models.breeding import BreedingEgg
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot

        touched = None
        try:
            with self.locked_cycle(cycle_id) as (cycle, (characters, storages, trainers)):
                if cycle.state == "collected":
                    return cycle.receipt
                if cycle.state != "producing":
                    raise OwnershipError("That cycle was cancelled; its fee/cooldown and planned outcome remain recorded.")
                assert_character_free(characters[self.actor_id])
                if cycle.ready_at > self.clock():
                    raise OwnershipError(f"This egg is not ready until {cycle.ready_at.isoformat()}. Status does not advance time.")
                entries, sources = self._parents(storages[self.actor_id], cycle_id=cycle.pk)
                if {source.pk for source in sources} != {cycle.parent_a_uuid, cycle.parent_b_uuid}:
                    raise OwnershipError("The recorded parents need staff inspection; no egg was created.")
                if OwnedPokemon.objects.filter(pk=cycle.egg_uuid).exists() or BreedingEgg.objects.filter(pk=cycle.egg_uuid).exists():
                    raise OwnershipError("The planned egg identity already exists unexpectedly; ask staff to inspect this cycle.")
                plan = cycle.plan
                touched = cycle.egg_uuid
                egg = create_owned_pokemon(plan["species"], trainers[self.actor_id], 1,
                    unique_id=cycle.egg_uuid, gender=plan["gender"], ability=plan["ability"], nature=plan["nature"],
                    ivs=plan["ivs"], evs=plan["evs"], active_move_names=plan["moves"], is_shiny=plan["is_shiny"],
                    is_egg=True, obtained_method="bred egg")
                active = list(ActiveMoveslot.objects.filter(pokemon=egg).order_by("slot").values_list("move__name", flat=True))
                if [normalize_name(move) for move in active] != [normalize_name(move) for move in plan["moves"]]:
                    raise OwnershipError("The planned hatch moves could not be initialized. Collection was rolled back; retry after review.")
                record = BreedingEgg.objects.create(id=egg.pk, cycle=cycle, pokemon=egg,
                    collected_at=self.clock(), hatch_ready_at=self.clock() + self.hatch_time)
                placement = egg.placement
                self._release_parents(cycle)
                cycle.state, cycle.closed_at = "collected", self.clock()
                cycle.receipt = {"cycle": str(cycle.pk), "egg": str(egg.pk), "owner": self.actor_id,
                    "location": placement.location_type, "slot": placement.slot, "box": placement.box_id,
                    "position": placement.box_position, "hatch_ready_at": record.hatch_ready_at.isoformat()}
                cycle.save(update_fields=["state", "closed_at", "receipt"])
                return cycle.receipt
        finally:
            if touched:
                self._reset_owned(touched)

    def hatch(self, egg_id):
        """The current owner hatches the same egg once, including after consent trading."""
        from pokemon.models.breeding import BreedingEgg
        from pokemon.models.core import OwnedPokemon

        identifier = self.identifier(egg_id)
        touched = False
        try:
            with locked_owners((self.actor_id,)) as (characters, storages, trainers):
                record = BreedingEgg.objects.select_for_update().filter(pk=identifier).first()
                if record is None:
                    raise OwnershipError("No supported bred egg has that ID.")
                if not OwnedPokemon.objects.filter(pk=identifier, trainer_id=trainers[self.actor_id].pk).exists():
                    if record.pokemon_id is None and record.hatch_owner_id == self.actor_id:
                        return record.hatch_receipt
                    raise OwnershipError("That egg does not belong to this character or was released.")
                touched = True
                if record.hatched_at:
                    return record.hatch_receipt
                assert_character_free(characters[self.actor_id])
                source, placement = PlacementService(storages[self.actor_id])._pokemon(fresh_owned(identifier, lock=True), storages[self.actor_id])
                if not source.is_egg or placement is None or placement.location_type not in ("party", "box"):
                    raise OwnershipError("This egg's state needs staff inspection; no Pokemon was created.")
                if record.hatch_ready_at > self.clock():
                    raise OwnershipError(f"This egg can hatch after {record.hatch_ready_at.isoformat()}.")
                plan = record.cycle.plan
                if any(getattr(source, field) != plan[field] for field in ("species", "gender", "ability", "nature", "ivs", "evs", "is_shiny")):
                    raise OwnershipError("The egg differs from its sealed genetic outcome; ask staff to inspect it.")
                source.is_egg = False
                source.original_trainer = trainers[self.actor_id]
                source.original_trainer_name = self.actor.key[:100]
                source.obtained_method = "hatched"
                source.met_date = self.clock()
                source.met_level = 1
                source.friendship = 100  # Explicit bounded PF2 hatch baseline.
                source.save(update_fields=["is_egg", "original_trainer", "original_trainer_name", "obtained_method", "met_date", "met_level", "friendship"])
                record.hatched_at, record.hatch_owner_id = self.clock(), self.actor_id
                record.hatch_receipt = {"egg": str(identifier), "pokemon": str(identifier), "owner": self.actor_id,
                    "species": source.species, "state": "hatched"}
                record.save(update_fields=["hatched_at", "hatch_owner_id", "hatch_receipt"])
                return record.hatch_receipt
        finally:
            if touched:
                self._reset_owned(identifier)

    @staticmethod
    def _reset_owned(identifier):
        """Flush provisional SharedMemory fields after success or rollback, including new eggs."""
        from django.db import connection
        from pokemon.models.core import OwnedPokemon

        cached = OwnedPokemon.get_cached_instance(identifier)
        if cached is not None:
            OwnedPokemon.flush_cached_instance(cached)
        def refresh():
            """A later legitimate release must never be undone by cache publication."""
            if OwnedPokemon.objects.filter(pk=identifier).exists():
                fresh_owned(identifier)
        if connection.in_atomic_block:
            transaction.on_commit(refresh, robust=True)
        else:
            refresh()

    def cycles(self):
        """Show only this origin character's immutable production outcomes after reconnect."""
        from django.db.models import Case, Value, When
        from pokemon.models.breeding import BreedingCycle

        return list(BreedingCycle.objects.filter(origin_character_id=self.actor_id).order_by(
            Case(When(state="producing", then=Value(0)), default=Value(1)), "-started_at")[:30])

    def eggs(self):
        """Only the current owner sees current egg/hatch availability, including gifts."""
        from pokemon.models.breeding import BreedingEgg
        from django.db.models import Case, Value, When

        return list(BreedingEgg.objects.filter(pokemon__trainer__user_id=self.actor_id).order_by(
            Case(When(hatched_at__isnull=True, then=Value(0)), default=Value(1)), "-collected_at")[:30])

    @staticmethod
    def describe(cycle):
        """A creator's historical plan never exposes the future owner's live Pokemon."""
        return (f"Cycle {cycle.pk}: {cycle.state}; offspring {cycle.plan['species']}; planned egg {cycle.egg_uuid}. "
            f"Fee paid once: {cycle.fee}. Ready {cycle.ready_at.isoformat()}; parent cooldown until {cycle.next_ready_at.isoformat()}. "
            f"Use +breed collect {cycle.pk} when ready, or +breed cancel {cycle.pk} (no refund; cooldown remains).")

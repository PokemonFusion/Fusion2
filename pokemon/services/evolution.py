"""Atomic, owner-validated evolution and held-item transitions."""

from contextlib import contextmanager
from copy import copy
from hashlib import sha256

from django.db import transaction

from pokemon.data.evolution import (
    EvolutionContext,
    attempt_evolution,
    evolution_options,
    normalize_name,
)
from pokemon.services.placement import PlacementError, PlacementService


class EvolutionError(ValueError):
    """A lifecycle request failed validation without changing any state."""


def resolve_item(query):
    """Resolve one full dex item name/key; reject unknown or ambiguous names."""
    from pokemon.dex import ITEMDEX

    query = normalize_name(query)
    matches = {}
    for key, data in ITEMDEX.items():
        display = data.raw.get("name") or data.name
        if query and query in {normalize_name(key), normalize_name(display)}:
            matches[key.lower()] = display
    if len(matches) != 1:
        raise EvolutionError("Use a complete, unambiguous item name.")
    return next(iter(matches.items()))


class EvolutionService:
    """Serialize storage, trainer inventory, and Pokemon writes in that order."""

    def __init__(self, caller):
        self.caller = caller
        self.placement = PlacementService(caller.storage)

    @contextmanager
    def locked(self, mon=None, slot=None):
        """Read fresh locked rows and restore Evennia's shared instance on failure."""
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.storage import PokemonPlacement
        from pokemon.models.trainer import Trainer

        pokemon = cached = None
        try:
            with self.placement.locked() as storage:
                if storage.user_id != self.caller.pk:
                    raise EvolutionError("Storage does not belong to you.")
                trainer = Trainer.objects.select_for_update().get(user_id=storage.user_id)
                if slot is not None:
                    placement = PokemonPlacement.objects.filter(
                        storage=storage, location_type="party", slot=slot
                    ).first()
                    if not placement:
                        raise EvolutionError("No Pokémon in that slot.")
                    mon = placement.pokemon
                # values() bypasses Evennia's identity map. refresh_from_db()
                # alone can read the same stale cached object back into itself.
                row = OwnedPokemon.objects.select_for_update().filter(pk=mon.pk).values().get()
                cached = OwnedPokemon.objects.get(pk=mon.pk)
                self._restore_row(cached, row)
                pokemon, placement = self.placement._pokemon(cached, storage)
                pokemon = copy(pokemon)
                pokemon._state = copy(pokemon._state)
                self.placement._check_reservation(placement, False)
                if pokemon.is_egg:
                    raise EvolutionError("Eggs cannot evolve or hold items.")
                yield pokemon, trainer, storage
                transaction.on_commit(trainer._sync_character_inventory)
        except (OwnedPokemon.DoesNotExist, PlacementError) as error:
            raise EvolutionError(str(error)) from error
        finally:
            # Model instances are not rolled back by transaction.atomic(). This also
            # handles stale references from Evennia's identity mapper after success.
            if pokemon is not None:
                row = OwnedPokemon.objects.filter(pk=pokemon.pk).values().get()
                for instance in (pokemon, cached, mon):
                    if instance is not None:
                        self._restore_row(instance, row)
                OwnedPokemon.cache_instance(cached)

    @staticmethod
    def _restore_row(pokemon, row):
        """Restore scalar fields and clear cached relations without identity lookup."""
        for name, value in row.items():
            setattr(pokemon, name, value)
        pokemon._state.fields_cache.clear()
        for attr in ("_cached_stats", "_types_override", "_prefetched_objects_cache"):
            pokemon.__dict__.pop(attr, None)

    def _context(self, pokemon, storage):
        """Build evidence from server state, never command-supplied condition flags."""
        from pokemon.data.evolution import lookup_species
        from pokemon.dex import MOVEDEX
        from pokemon.helpers.pokemon_helpers import get_stats

        moves = tuple(pokemon.activemoveslot_set.values_list("move__name", flat=True))
        move_names = {normalize_name(m) for m in moves}
        move_types = tuple(
            m.raw.get("type", "")
            for k, m in MOVEDEX.items()
            if normalize_name(k) in move_names or normalize_name(m.name) in move_names
        )
        party = list(storage.placements.filter(location_type="party").values_list("pokemon__species", flat=True))
        types = tuple(t for s in party if (data := lookup_species(s)) for t in data.types)
        room = getattr(self.caller, "location", None)
        db = getattr(room, "db", None)
        stats = get_stats(pokemon)
        return EvolutionContext(
            friendship=pokemon.friendship,
            moves=moves,
            move_types=move_types,
            held_item=pokemon.held_item,
            gender=pokemon.gender,
            ability=pokemon.ability,
            nature=pokemon.nature,
            time=getattr(db, "time_of_day", "") or "",
            weather=getattr(db, "weather", "") or "",
            region=getattr(db, "region", "") or "",
            magnetic_field=getattr(db, "magnetic_field", False) is True,
            party_species=tuple(party),
            party_types=types,
            stats={"atk": stats.get("attack"), "def": stats.get("defense")},
        )

    @staticmethod
    def _inventory_key(trainer, item_key):
        """Accept historical display-name rows without unsafe partial matching."""
        matches = [
            e.item_name
            for e in trainer.inventory.select_for_update().all()
            if normalize_name(e.item_name) == normalize_name(item_key) and e.quantity > 0
        ]
        if len(matches) > 1:
            raise EvolutionError("Ambiguous inventory entries; ask staff to consolidate them.")
        return matches[0] if matches else None

    def evolve(self, mon, *, item=None, target=None):
        """Consume exactly one required item and persist one eligible transition."""
        item_key, display = resolve_item(item) if item else (None, None)
        with self.locked(mon) as (pokemon, trainer, storage):
            # A repeated implicit command at the same level must not evolve a
            # second stage. An explicit different target expresses a new request.
            signature = f"{pokemon.level}:{item_key or ''}:{normalize_name(target or '')}"
            receipt = "evo:" + sha256(signature.encode()).hexdigest()[:40]
            if receipt in pokemon.flags:
                return None
            context = self._context(pokemon, storage)
            options = evolution_options(pokemon.species, level=pokemon.level, item=display, context=context)
            if target:
                options = [e for e in options if normalize_name(e.name) == normalize_name(target)]
            if len(options) != 1:
                if options:
                    raise EvolutionError("Choose an evolution with =<target>: " + ", ".join(e.name for e in options))
                raise EvolutionError(
                    "It doesn't seem to be able to evolve right now (condition or target unavailable)."
                )
            if item_key:
                stored_key = self._inventory_key(trainer, item_key)
                if not stored_key or not trainer.remove_item(stored_key):
                    raise EvolutionError(f"You do not have a {display}.")
            result = attempt_evolution(pokemon, item=display, context=context, target=options[0].name)
            if not result:
                raise EvolutionError("Evolution conditions changed; try again.")
            pokemon.flags = [f for f in pokemon.flags if not f.startswith("evo:")] + [receipt]
            pokemon.save()
            return result

    def hold(self, slot, item=None):
        """Equip, replace or remove; return old items to the trainer's inventory."""
        if slot not in range(1, 7):
            raise EvolutionError("Slot must be a number between 1 and 6.")
        item_key, display = resolve_item(item) if item else (None, None)
        with self.locked(slot=slot) as (pokemon, trainer, _storage):
            previous = pokemon.held_item or ""
            if normalize_name(previous) == "nothing":
                previous = ""
            if normalize_name(previous) == normalize_name(display or ""):
                return f"{pokemon.name} is already holding {display or 'nothing'}."
            if item_key:
                stored_key = self._inventory_key(trainer, item_key)
                if stored_key:
                    if not trainer.remove_item(stored_key):
                        raise EvolutionError(f"You do not have a {display}.")
                else:
                    self._consume_carried(item_key)
            if previous:
                # Unknown legacy held names are returned verbatim, never discarded.
                try:
                    old_key, _ = resolve_item(previous)
                except EvolutionError:
                    old_key = previous.lower()
                old_key = self._inventory_key(trainer, old_key) or old_key
                trainer.add_item(old_key)
            pokemon.held_item = display or ""
            pokemon.save()
            return (
                f"{pokemon.name} is now holding {display}."
                if display
                else f"{pokemon.name}'s {previous} was returned to your inventory."
            )

    def _consume_carried(self, key):
        """Bridge legacy carried objects using exact, locked identity/location."""
        from evennia.objects.models import ObjectDB

        objects = (
            ObjectDB.objects.select_for_update()
            .filter(db_location_id=self.caller.pk)
            .order_by("pk")
            .values("pk", "db_key")
        )
        matches = [obj for obj in objects if normalize_name(obj["db_key"]) == normalize_name(key)]
        if len(matches) != 1:
            raise EvolutionError("Item not found, or multiple carried items match; use your trainer inventory.")
        # QuerySet deletion avoids typeclass callbacks/identity-cache side effects
        # before commit. Held items store a dex name, not arbitrary object metadata.
        obj = ObjectDB.objects.get(pk=matches[0]["pk"])
        ObjectDB.objects.filter(pk=obj.pk, db_location_id=self.caller.pk).delete()

        def publish_removal():
            """Invalidate object and contents caches only once deletion commits."""
            ObjectDB.flush_cached_instance(obj)
            owner = ObjectDB.objects.get(pk=self.caller.pk)
            owner.contents_cache.init()

        transaction.on_commit(publish_removal, robust=True)

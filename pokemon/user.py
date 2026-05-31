"""Character typeclass for players and their Pokémon interactions."""

from typing import TYPE_CHECKING

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone
from typeclasses.characters import Character

from pokemon.data.starters import resolve_starter_key
from pokemon.helpers.party_helpers import (
    get_active_party as _get_active_party,
    has_usable_pokemon as _has_usable_party,
)
from pokemon.helpers.pokemon_helpers import create_owned_pokemon
from pokemon.models.storage import PokemonPlacement, move_to_box, move_to_party
from utils.inventory import Inventory, InventoryMixin

# Helper to resolve settings-provided locations into actual ObjectDBs
try:
    from pokemon.utils.objresolve import resolve_to_obj
except Exception:  # pragma: no cover - fallback during import issues
    from evennia.objects.models import ObjectDB
    from evennia.utils.search import search_object

    def resolve_to_obj(val):
        """Fallback object resolver for startup."""
        if callable(val):  # callable -> call
            val = val()
        if isinstance(val, str) and val.startswith("#") and val[1:].isdigit():
            return ObjectDB.objects.filter(id=int(val[1:])).first()
        if isinstance(val, int):  # integer id
            return ObjectDB.objects.filter(id=val).first()
        if isinstance(val, ObjectDB):  # already an ObjectDB instance
            return val
        if isinstance(val, str):  # name lookup as last resort
            objs = search_object(val)
            return objs[0] if objs else None
        return None


if TYPE_CHECKING:  # pragma: no cover - type checking only
    from .models import GymBadge, StorageBox, Trainer, UserStorage


class User(Character, InventoryMixin):
    def _create_owned_pokemon(self, name, level, data=None):
        """Create and return a fully initialized ``OwnedPokemon``."""
        data = data or {}
        return create_owned_pokemon(
            name,
            self.trainer,
            level,
            gender=data.get("gender", ""),
            nature=data.get("nature", ""),
            ability=data.get("ability", ""),
            ivs=data.get("ivs"),
            evs=data.get("evs"),
        )

    def add_pokemon_to_user(self, name, level, type_, data=None):
        pokemon = self._create_owned_pokemon(name, level, data)
        self.storage.add_active_pokemon(pokemon)

    def add_pokemon_to_storage(self, name, level, type_, data=None):
        pokemon = self._create_owned_pokemon(name, level, data)
        box = self.get_box(1)
        move_to_box(pokemon, self.storage, box)

    def show_pokemon_on_user(self):
        party = self.storage.get_party()
        return "\n".join(
            f"{pokemon} - caught {timezone.localtime(pokemon.created_at):%Y-%m-%d %H:%M:%S}" for pokemon in party
        )

    def show_pokemon_in_storage(self):
        return "\n".join(
            f"{pokemon} - caught {timezone.localtime(pokemon.created_at):%Y-%m-%d %H:%M:%S}"
            for pokemon in self.storage.get_stored_pokemon()
        )

    def at_object_creation(self):
        super().at_object_creation()
        # Resolve DEFAULT_HOME to an ObjectDB before assignment
        try:
            home = resolve_to_obj(getattr(settings, "DEFAULT_HOME", None))
            if home:
                self.home = home
        except Exception:
            pass

        # Resolve START_LOCATION similarly (optional; only if setting exists)
        try:
            start_loc = resolve_to_obj(getattr(settings, "START_LOCATION", None))
            if start_loc:
                self.location = start_loc
        except Exception:
            pass

        # Ensure a storage record and starter boxes exist for this character.
        _ = self.storage
        Trainer = apps.get_model("pokemon", "Trainer")
        # allocate next available trainer number to avoid unique collisions
        next_number = (Trainer.objects.aggregate(max_num=Max("trainer_number"))["max_num"] or 0) + 1
        while True:
            try:
                Trainer.objects.get_or_create(user=self, defaults={"trainer_number": next_number})
            except IntegrityError:
                next_number += 1
                continue
            break
        if self.db.inventory is None:
            from utils.inventory import Inventory

            self.db.inventory = Inventory()

    @property
    def storage(self) -> "UserStorage":
        """Return this character's storage, creating it if needed."""
        UserStorage = apps.get_model("pokemon", "UserStorage")
        storage, _ = UserStorage.objects.get_or_create(user=self)
        from .models.storage import ensure_boxes

        ensure_boxes(storage)
        return storage

    def get_active_party(self):
        """Return the list of active Pokémon for this character."""

        return _get_active_party(self)

    def has_usable_pokemon(self) -> bool:
        """Return ``True`` if at least one active Pokémon can battle."""

        return _has_usable_party(self)

    # ------------------------------------------------------------------
    # Starter selection
    # ------------------------------------------------------------------
    def choose_starter(self, species_name: str) -> str:
        """Deprecated direct starter creation shortcut."""

        if not resolve_starter_key(species_name):
            return "That is not a valid starter species. Use |w+starters|n to list valid starters."
        if self.storage.has_party_pokemon():
            return "You already have your starter."
        return (
            "Direct starter selection has moved into chargen. "
            "Use |w+starter|n with no Pokémon name to open or resume starter selection."
        )

    # ------------------------------------------------------------------
    # Box management
    # ------------------------------------------------------------------

    def get_box(self, index: int) -> "StorageBox":
        boxes = list(self.storage.boxes.all().order_by("id"))
        if index < 1 or index > len(boxes):
            raise ValueError("Invalid box number")
        return boxes[index - 1]

    def deposit_pokemon(self, pokemon_id: str, box_index: int = 1) -> str:
        """Deposit a Pokémon into a storage box if possible."""

        pokemon = self.get_pokemon_by_id(pokemon_id)
        if not pokemon:
            return "No such Pokémon."

        if not self._pokemon_is_in_party(pokemon):
            return "That Pokemon is not in your party."
        try:
            box = self.get_box(box_index)
        except ValueError:
            return "Invalid box number."
        with transaction.atomic():
            move_to_box(pokemon, self.storage, box)
        display = pokemon.nickname or pokemon.species
        return f"{display} was deposited in {box.name}."

    def withdraw_pokemon(self, pokemon_id: str, box_index: int = 1) -> str:
        pokemon = self.get_pokemon_by_id(pokemon_id)
        if not pokemon:
            return "No such Pokémon."
        try:
            box = self.get_box(box_index)
        except ValueError:
            return "Invalid box number."
        if pokemon not in box.get_pokemon():
            return "That Pokémon is not in that box."
        if self.storage.active_pokemon_count() >= 6:
            return "Your party is full. Use swap <pokemon_id> <party_slot> [box] to swap with a party Pokemon."
        with transaction.atomic():
            move_to_party(pokemon, self.storage)
        display = pokemon.nickname or pokemon.species
        return f"{display} was withdrawn from {box.name}."

    def swap_pokemon(self, pokemon_id: str, party_slot: int, box_index: int = 1) -> str:
        """Swap a boxed Pokemon into a party slot."""

        if party_slot < 1 or party_slot > 6:
            return "Party slot must be between 1 and 6."

        pokemon = self.get_pokemon_by_id(pokemon_id)
        if not pokemon:
            return "No such Pokemon."
        try:
            box = self.get_box(box_index)
        except ValueError:
            return "Invalid box number."
        if pokemon not in box.get_pokemon():
            return "That Pokemon is not in that box."

        party_pokemon = self.get_active_pokemon_by_slot(party_slot)
        with transaction.atomic():
            if party_pokemon:
                move_to_box(party_pokemon, self.storage, box)
            move_to_party(pokemon, self.storage, party_slot)

        display = pokemon.nickname or pokemon.species
        if not party_pokemon:
            return f"{display} was withdrawn to party slot {party_slot}."
        party_display = party_pokemon.nickname or party_pokemon.species
        return f"{display} was swapped into slot {party_slot}; {party_display} was sent to {box.name}."

    def show_box(self, box_index: int) -> str:
        try:
            box = self.get_box(box_index)
        except ValueError:
            return "Invalid box number."
        mons = box.get_pokemon()
        if not mons:
            return f"{box.name} is empty."
        return "\n".join(str(p) for p in mons)

    def get_pokemon_by_id(self, pokemon_id):
        OwnedPokemon = apps.get_model("pokemon", "OwnedPokemon")
        try:
            pokemon = OwnedPokemon.objects.filter(unique_id=pokemon_id, trainer=self.trainer).first()
            if pokemon:
                return pokemon
            return OwnedPokemon.objects.filter(unique_id=pokemon_id, placement__storage=self.storage).first()
        except (OwnedPokemon.DoesNotExist, ValidationError, ValueError):
            return None

    def _pokemon_is_in_party(self, pokemon) -> bool:
        return self.storage.placements.filter(
            pokemon=pokemon,
            location_type=PokemonPlacement.LocationType.PARTY,
        ).exists()

    def get_active_pokemon_by_slot(self, slot: int):
        """Return the active Pokémon at the given slot (1-6)."""
        slot_obj = self.storage.active_slots.select_related("pokemon").filter(slot=slot).first()
        return slot_obj.pokemon if slot_obj else None

    @property
    def trainer(self) -> "Trainer":
        Trainer = apps.get_model("pokemon", "Trainer")
        trainer, _ = Trainer.objects.get_or_create(user=self, defaults={"trainer_number": Trainer.objects.count() + 1})
        return trainer

    def _update_inventory_cache_from_trainer(self) -> None:
        """Synchronize the cached inventory with the trainer's records."""

        try:
            entries = self.trainer.list_inventory()
        except Exception:
            entries = []
        cache = Inventory()
        for entry in entries:
            cache[entry.item_name.title()] = entry.quantity
        self.db.inventory = cache

    def add_item(self, name: str, quantity: int = 1) -> None:
        """Add an item by delegating to the underlying trainer record."""

        trainer = self.trainer
        trainer.add_item(name, quantity)

    def remove_item(self, name: str, quantity: int = 1) -> bool:
        """Remove an item via the trainer, returning success."""

        trainer = self.trainer
        return trainer.remove_item(name, quantity)

    def has_item(self, name: str, quantity: int = 1) -> bool:
        """Return ``True`` if the trainer has at least ``quantity`` of ``name``."""

        trainer = self.trainer
        return trainer.has_item(name, quantity)

    # Helper proxy methods
    def add_badge(self, badge: "GymBadge") -> None:
        self.trainer.add_badge(badge)

    def add_money(self, amount: int) -> None:
        self.trainer.add_money(amount)

    def spend_money(self, amount: int) -> bool:
        """Try to spend money from the trainer."""
        return self.trainer.spend_money(amount)

    def log_seen_pokemon(self, species: str | int) -> None:
        """Proxy for ``Trainer.log_seen_pokemon``."""
        self.trainer.log_seen_pokemon(species)

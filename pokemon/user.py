"""Character typeclass for players and their Pokémon interactions."""

from typing import TYPE_CHECKING

from django.apps import apps
from django.conf import settings
from django.utils import timezone
from evennia import DefaultCharacter

from pokemon.helpers.pokemon_helpers import create_owned_pokemon
from utils.inventory import InventoryMixin

from .data.generation import generate_pokemon
from .dex import POKEDEX

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


class User(DefaultCharacter, InventoryMixin):
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
        self.storage.stored_pokemon.add(pokemon)

    def show_pokemon_on_user(self):
        party = (
            self.storage.get_party() if hasattr(self.storage, "get_party") else list(
                self.storage.active_pokemon.all())
        )
        return "\n".join(
            f"{pokemon} - caught {timezone.localtime(pokemon.created_at):%Y-%m-%d %H:%M:%S}" for pokemon in party
        )

    def show_pokemon_in_storage(self):
        return "\n".join(
            f"{pokemon} - caught {timezone.localtime(pokemon.created_at):%Y-%m-%d %H:%M:%S}"
            for pokemon in self.storage.stored_pokemon.all()
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
        Trainer.objects.get_or_create(
            user=self, defaults={"trainer_number": Trainer.objects.count() + 1}
        )
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

    # ------------------------------------------------------------------
    # Starter selection
    # ------------------------------------------------------------------
    def choose_starter(self, species_name: str) -> str:
        """Give the player their first Pokémon."""

        if self.storage.active_pokemon.exists():
            return "You already have your starter."

        species = POKEDEX.get(species_name.lower())
        if not species:
            return "That species does not exist."

        instance = generate_pokemon(species.name, level=5)
        data = {
            "gender": instance.gender,
            "nature": instance.nature,
            "ability": instance.ability,
            "ivs": [
                instance.ivs.hp,
                instance.ivs.attack,
                instance.ivs.defense,
                instance.ivs.special_attack,
                instance.ivs.special_defense,
                instance.ivs.speed,
            ],
            "evs": [0, 0, 0, 0, 0, 0],
        }
        pokemon = self._create_owned_pokemon(instance.species.name, 5, data)
        self.storage.add_active_pokemon(pokemon)
        return f"You received {pokemon.species}!"

    # ------------------------------------------------------------------
    # Box management
    # ------------------------------------------------------------------

    def get_box(self, index: int) -> "StorageBox":
        boxes = list(self.storage.boxes.all().order_by("id"))
        if index < 1 or index > len(boxes):
            raise ValueError("Invalid box number")
        return boxes[index - 1]

    def deposit_pokemon(self, pokemon_id: str, box_index: int = 1) -> str:
        pokemon = self.get_pokemon_by_id(pokemon_id)
        if not pokemon:
            return "No such Pokémon."
        if pokemon in self.storage.active_pokemon.all():
            self.storage.remove_active_pokemon(pokemon)
        self.storage.stored_pokemon.add(pokemon)
        box = self.get_box(box_index)
        box.pokemon.add(pokemon)
        display = pokemon.nickname or pokemon.species
        return f"{display} was deposited in {box.name}."

    def withdraw_pokemon(self, pokemon_id: str, box_index: int = 1) -> str:
        pokemon = self.get_pokemon_by_id(pokemon_id)
        if not pokemon:
            return "No such Pokémon."
        box = self.get_box(box_index)
        if pokemon not in box.pokemon.all():
            return "That Pokémon is not in that box."
        box.pokemon.remove(pokemon)
        self.storage.stored_pokemon.remove(pokemon)
        self.storage.add_active_pokemon(pokemon)
        display = pokemon.nickname or pokemon.species
        return f"{display} was withdrawn from {box.name}."

    def show_box(self, box_index: int) -> str:
        box = self.get_box(box_index)
        mons = box.pokemon.all()
        if not mons:
            return f"{box.name} is empty."
        return "\n".join(str(p) for p in mons)

    def get_pokemon_by_id(self, pokemon_id):
        OwnedPokemon = apps.get_model("pokemon", "OwnedPokemon")
        try:
            return OwnedPokemon.objects.get(unique_id=pokemon_id)
        except OwnedPokemon.DoesNotExist:
            return None

    def get_active_pokemon_by_slot(self, slot: int):
        """Return the active Pokémon at the given slot (1-6)."""
        slot_obj = self.storage.active_slots.select_related(
            "pokemon").filter(slot=slot).first()
        return slot_obj.pokemon if slot_obj else None

    @property
    def trainer(self) -> "Trainer":
        Trainer = apps.get_model("pokemon", "Trainer")
        trainer, _ = Trainer.objects.get_or_create(
            user=self, defaults={"trainer_number": Trainer.objects.count() + 1}
        )
        return trainer

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

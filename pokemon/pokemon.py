from evennia import DefaultCharacter
from .models import Pokemon, UserStorage, StorageBox, Trainer, GymBadge
from .generation import generate_pokemon
from .dex import POKEDEX
from utils.inventory import InventoryMixin


class User(InventoryMixin, DefaultCharacter):
    def add_pokemon_to_user(self, name, level, type_, data=None):
        pokemon = Pokemon.objects.create(
            name=name,
            level=level,
            type_=type_,
            trainer=self.trainer,
            data=data or {},
        )
        self.storage.active_pokemon.add(pokemon)
    def add_pokemon_to_storage(self, name, level, type_, data=None):
        pokemon = Pokemon.objects.create(
            name=name,
            level=level,
            type_=type_,
            trainer=self.trainer,
            data=data or {},
        )
        self.storage.stored_pokemon.add(pokemon)

    def show_pokemon_on_user(self):
        return "\n".join(str(pokemon) for pokemon in self.storage.active_pokemon.all())

    def show_pokemon_in_storage(self):
        return "\n".join(str(pokemon) for pokemon in self.storage.stored_pokemon.all())

    def at_object_creation(self):
        super().at_object_creation()
        # Ensure a storage record and starter boxes exist for this character.
        _ = self.storage
        Trainer.objects.get_or_create(
            user=self, defaults={"trainer_number": Trainer.objects.count() + 1}
        )
        if self.db.inventory is None:
            self.db.inventory = {}

    @property
    def storage(self) -> UserStorage:
        """Return this character's storage, creating it if needed."""
        storage, created = UserStorage.objects.get_or_create(user=self)
        if not storage.boxes.exists():
            for i in range(1, 9):
                StorageBox.objects.create(storage=storage, name=f"Box {i}")
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
        pokemon = Pokemon.objects.create(
            name=instance.species.name,
            level=instance.level,
            type_=", ".join(instance.species.types),
            trainer=self.trainer,
        )
        self.storage.active_pokemon.add(pokemon)
        return f"You received {pokemon.name}!"

    # ------------------------------------------------------------------
    # Box management
    # ------------------------------------------------------------------

    def get_box(self, index: int) -> StorageBox:
        boxes = list(self.storage.boxes.all().order_by("id"))
        if index < 1 or index > len(boxes):
            raise ValueError("Invalid box number")
        return boxes[index - 1]

    def deposit_pokemon(self, pokemon_id: int, box_index: int = 1) -> str:
        pokemon = self.get_pokemon_by_id(pokemon_id)
        if not pokemon:
            return "No such Pokémon."
        if pokemon in self.storage.active_pokemon.all():
            self.storage.active_pokemon.remove(pokemon)
        self.storage.stored_pokemon.add(pokemon)
        box = self.get_box(box_index)
        box.pokemon.add(pokemon)
        return f"{pokemon.name} was deposited in {box.name}."

    def withdraw_pokemon(self, pokemon_id: int, box_index: int = 1) -> str:
        pokemon = self.get_pokemon_by_id(pokemon_id)
        if not pokemon:
            return "No such Pokémon."
        box = self.get_box(box_index)
        if pokemon not in box.pokemon.all():
            return "That Pokémon is not in that box."
        box.pokemon.remove(pokemon)
        self.storage.stored_pokemon.remove(pokemon)
        self.storage.active_pokemon.add(pokemon)
        return f"{pokemon.name} was withdrawn from {box.name}."

    def show_box(self, box_index: int) -> str:
        box = self.get_box(box_index)
        mons = box.pokemon.all()
        if not mons:
            return f"{box.name} is empty."
        return "\n".join(str(p) for p in mons)

    def get_pokemon_by_id(self, pokemon_id):
        try:
            return Pokemon.objects.get(id=pokemon_id)
        except Pokemon.DoesNotExist:
            return None

    def get_active_pokemon_by_slot(self, slot: int):
        """Return the active Pokémon at the given slot (1-6)."""
        mons = list(self.storage.active_pokemon.all().order_by("id"))
        if 1 <= slot <= len(mons):
            return mons[slot - 1]
        return None

    @property
    def trainer(self) -> Trainer:
        trainer, _ = Trainer.objects.get_or_create(
            user=self, defaults={"trainer_number": Trainer.objects.count() + 1}
        )
        return trainer

    # Helper proxy methods
    def add_badge(self, badge: GymBadge) -> None:
        self.trainer.add_badge(badge)

    def add_money(self, amount: int) -> None:
        self.trainer.add_money(amount)

    def spend_money(self, amount: int) -> bool:
        """Try to spend money from the trainer."""
        return self.trainer.spend_money(amount)

    def log_seen_pokemon(self, pokemon: Pokemon) -> None:
        self.trainer.log_seen_pokemon(pokemon)

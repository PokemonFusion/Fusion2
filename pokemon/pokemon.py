from evennia import DefaultCharacter
from .models import (
    Pokemon,
    OwnedPokemon,
    UserStorage,
    StorageBox,
    Trainer,
    GymBadge,
)
from .generation import generate_pokemon
from .dex import POKEDEX
from utils.inventory import InventoryMixin


class User(DefaultCharacter, InventoryMixin):
    def add_pokemon_to_user(self, name, level, type_, data=None):
        pokemon = OwnedPokemon.objects.create(
            trainer=self.trainer,
            species=name,
            nickname="",
            gender=data.get("gender", "") if data else "",
            nature=data.get("nature", "") if data else "",
            ability=data.get("ability", "") if data else "",
            ivs=data.get("ivs", [0, 0, 0, 0, 0, 0]) if data else [0, 0, 0, 0, 0, 0],
            evs=data.get("evs", [0, 0, 0, 0, 0, 0]) if data else [0, 0, 0, 0, 0, 0],
        )
        self.storage.active_pokemon.add(pokemon)
    def add_pokemon_to_storage(self, name, level, type_, data=None):
        pokemon = OwnedPokemon.objects.create(
            trainer=self.trainer,
            species=name,
            nickname="",
            gender=data.get("gender", "") if data else "",
            nature=data.get("nature", "") if data else "",
            ability=data.get("ability", "") if data else "",
            ivs=data.get("ivs", [0, 0, 0, 0, 0, 0]) if data else [0, 0, 0, 0, 0, 0],
            evs=data.get("evs", [0, 0, 0, 0, 0, 0]) if data else [0, 0, 0, 0, 0, 0],
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
        pokemon = OwnedPokemon.objects.create(
            trainer=self.trainer,
            species=instance.species.name,
            nickname="",
            gender=instance.gender,
            nature=instance.nature,
            ability=instance.ability,
            ivs=[
                instance.ivs.hp,
                instance.ivs.atk,
                instance.ivs.def_,
                instance.ivs.spa,
                instance.ivs.spd,
                instance.ivs.spe,
            ],
            evs=[0, 0, 0, 0, 0, 0],
        )
        self.storage.active_pokemon.add(pokemon)
        return f"You received {pokemon.species}!"

    # ------------------------------------------------------------------
    # Box management
    # ------------------------------------------------------------------

    def get_box(self, index: int) -> StorageBox:
        boxes = list(self.storage.boxes.all().order_by("id"))
        if index < 1 or index > len(boxes):
            raise ValueError("Invalid box number")
        return boxes[index - 1]

    def deposit_pokemon(self, pokemon_id: str, box_index: int = 1) -> str:
        pokemon = self.get_pokemon_by_id(pokemon_id)
        if not pokemon:
            return "No such Pokémon."
        if pokemon in self.storage.active_pokemon.all():
            self.storage.active_pokemon.remove(pokemon)
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
        self.storage.active_pokemon.add(pokemon)
        display = pokemon.nickname or pokemon.species
        return f"{display} was withdrawn from {box.name}."

    def show_box(self, box_index: int) -> str:
        box = self.get_box(box_index)
        mons = box.pokemon.all()
        if not mons:
            return f"{box.name} is empty."
        return "\n".join(str(p) for p in mons)

    def get_pokemon_by_id(self, pokemon_id):
        try:
            return OwnedPokemon.objects.get(unique_id=pokemon_id)
        except OwnedPokemon.DoesNotExist:
            return None

    def get_active_pokemon_by_slot(self, slot: int):
        """Return the active Pokémon at the given slot (1-6)."""
        mons = list(self.storage.active_pokemon.all().order_by("unique_id"))
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

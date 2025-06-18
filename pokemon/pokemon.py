from evennia import DefaultCharacter
from .models import Pokemon, UserStorage, StorageBox
from .generation import generate_pokemon
from .dex import POKEDEX
  
class User(DefaultCharacter):
    def add_pokemon_to_user(self, name, level, type_):
        pokemon = Pokemon.objects.create(name=name, level=level, type_=type_)
        self.storage.active_pokemon.add(pokemon)

    
    def add_pokemon_to_storage(self, name, level, type_):
        pokemon = Pokemon.objects.create(name=name, level=level, type_=type_)
        self.storage.stored_pokemon.add(pokemon)

    def show_pokemon_on_user(self):
        return "\n".join(str(pokemon) for pokemon in self.storage.active_pokemon.all())

    def show_pokemon_in_storage(self):
        return "\n".join(str(pokemon) for pokemon in self.storage.stored_pokemon.all())

    def at_object_creation(self):
        super().at_object_creation()
        storage, _ = UserStorage.objects.get_or_create(user=self)
        self.storage = storage
        if not storage.boxes.exists():
            for i in range(1, 9):
                StorageBox.objects.create(storage=storage, name=f"Box {i}")

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

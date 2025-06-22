from evennia import DefaultCharacter
from .models import Pokemon, UserStorage
  
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
        storage, created = UserStorage.objects.get_or_create(user=self)
        self.storage = storage

    def get_pokemon_by_id(self, pokemon_id):
        try:
            return Pokemon.objects.get(id=pokemon_id)
        except Pokemon.DoesNotExist:
            return None

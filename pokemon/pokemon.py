from evennia import DefaultCharacter
from .models import Pokemon, UserStorage, Trainer, GymBadge
  
class User(DefaultCharacter):
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
        storage, _ = UserStorage.objects.get_or_create(user=self)
        self.storage = storage
        Trainer.objects.get_or_create(
            user=self, defaults={"trainer_number": Trainer.objects.count() + 1}
        )

    def get_pokemon_by_id(self, pokemon_id):
        try:
            return Pokemon.objects.get(id=pokemon_id)
        except Pokemon.DoesNotExist:
            return None

    @property
    def trainer(self) -> Trainer:
        return Trainer.objects.get(user=self)

    # Helper proxy methods
    def add_badge(self, badge: GymBadge) -> None:
        self.trainer.add_badge(badge)

    def add_money(self, amount: int) -> None:
        self.trainer.add_money(amount)

    def log_seen_pokemon(self, pokemon: Pokemon) -> None:
        self.trainer.log_seen_pokemon(pokemon)

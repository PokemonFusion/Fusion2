from .pokemon_middleware import Pokemon

class Player:
    def __init__(self, data):
        self.name = data['name']
        self.team = [Pokemon(p['name']) for p in data['team']]
        self.active = self.team[:2]  # Assuming the first two Pokémon are active
        # Additional setup...

    def is_defeated(self):
        return all(pokemon.is_fainted() for pokemon in self.team)

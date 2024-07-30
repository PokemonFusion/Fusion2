from fusion2.pokemon.pokedex import pokedex

class Pokemon:
    def __init__(self, name):
        if name not in pokedex:
            raise ValueError(f"Pokemon {name} not found in Pokedex.")
        
        data = pokedex[name]
        self.name = name
        self.hp = data['baseStats']['hp']
        self.attack = data['baseStats']['atk']
        self.defense = data['baseStats']['def']
        self.sp_attack = data['baseStats']['spa']
        self.sp_defense = data['baseStats']['spd']
        self.speed = data['baseStats']['spe']
        self.types = data['types']
        self.status = None
        # Additional setup...

    def is_fainted(self):
        return self.hp <= 0

from evennia import DefaultObject

class Pokemon(DefaultObject):
    """
    A class representing a Pokémon. This class stores Pokémon attributes in the database.
    """
    def at_object_creation(self):
        self.db.pokemon_id = None  # Unique ID for each Pokémon instance
        self.db.pokedex_number = None  # Pokedex number of the Pokémon
        self.db.owner = None  # The owner of the Pokémon (player or NPC)
        self.db.level = 1
        self.db.exp = 0
        self.db.current_hp = 0
        self.db.max_hp = 0
        self.db.known_moves = []
        self.db.ivs = {
            'hp': 0,
            'attack': 0,
            'defense': 0,
            'sp_attack': 0,
            'sp_defense': 0,
            'speed': 0
        }
        self.db.evs = {
            'hp': 0,
            'attack': 0,
            'defense': 0,
            'sp_attack': 0,
            'sp_defense': 0,
            'speed': 0
        }
        self.db.nature = ""

    def set_static_data(self, static_data):
        """
        Set static data from the pokedex.
        """
        self.db.name = static_data['name']
        self.db.base_stats = static_data['baseStats']

    def set_dynamic_data(self, pokemon_id, pokedex_number, owner, level, exp, current_hp, known_moves, ivs, evs, nature):
        """
        Set dynamic data for the Pokémon.
        """
        self.db.pokemon_id = pokemon_id
        self.db.pokedex_number = pokedex_number
        self.db.owner = owner
        self.db.level = level
        self.db.exp = exp
        self.db.current_hp = current_hp
        self.db.max_hp = self.calculate_stat('hp')
        self.db.known_moves = known_moves
        self.db.ivs = ivs
        self.db.evs = evs
        self.db.nature = nature

    def calculate_stat(self, stat):
        """
        Calculate the stat value based on base stats, IVs, EVs, and nature.
        """
        base = self.db.base_stats[stat]
        iv = self.db.ivs[stat]
        ev = self.db.evs[stat]
        level = self.db.level
        nature_modifier = 1  # Modify this based on the nature's effect on the stat

        if stat == 'hp':
            return ((2 * base + iv + (ev // 4)) * level // 100) + level + 10
        else:
            return (((2 * base + iv + (ev // 4)) * level // 100) + 5) * nature_modifier

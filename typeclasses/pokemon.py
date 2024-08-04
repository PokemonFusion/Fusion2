from evennia import DefaultObject
from utils.pokemon_utils import NATURES, calculate_stat, generate_ivs, get_status_effect
import random

class Pokemon(DefaultObject):
    def at_object_creation(self):
        self.db.pokemon_id = None
        self.db.species = "missingno"
        self.db.nickname = None
        self.db.gender = None
        self.db.nature = random.choice(list(NATURES.keys()))
        self.db.ability = None
        self.db.level = 1
        self.db.ivs = generate_ivs()
        self.db.evs = {stat: 0 for stat in ['hp', 'attack', 'defense', 'sp_attack', 'sp_defense', 'speed']}
        self.db.current_hp = 0
        self.db.max_hp = 0
        self.db.known_moves = []
        self.db.status = 0  # Assuming status is an integer

    def get_name(self):
        return self.db.nickname if self.db.nickname else self.db.species

    def set_species(self, species):
        self.db.species = species
        self.db.max_hp = calculate_stat(self, 'hp')
        self.db.current_hp = self.db.max_hp

    def set_nature(self, nature):
        self.db.nature = nature

    def set_level(self, level):
        self.db.level = level
        self.db.max_hp = calculate_stat(self, 'hp')
        self.db.current_hp = self.db.max_hp

class Status:
    def __init__(self):
        # these are the default values
        self.name = 0
        self.duration = -1  # -1 means indefinite duration

    def set_status(self, status: int):
        self.name, self.duration = get_status_effect(status)

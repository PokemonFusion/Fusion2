"""
Room

Rooms are simple containers that has no location of their own.

"""

from evennia.objects.objects import DefaultRoom
import random

from .objects import ObjectParent


class Room(ObjectParent, DefaultRoom):
    """
    Rooms are like any Object, except their location is None
    (which is default). They also use basetype_setup() to
    add locks so they cannot be puppeted or picked up.
    (to change that, use at_object_creation instead)

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Objects.
    """

    pass


class FusionRoom(Room):
    """Room with support for hunting and shop flags."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_pokemon_center = False
        self.db.is_item_store = False
        self.db.allow_hunting = False
        self.db.encounter_rate = 100
        self.db.hunt_chart = []

    def set_hunt_chart(self, chart):
        """Helper to set this room's hunt chart."""
        self.db.hunt_chart = chart

    def get_random_pokemon(self):
        """Return a Pokémon name selected from the hunt chart."""
        if not self.db.allow_hunting or not self.db.hunt_chart:
            return None
        population = [e.get("name") for e in self.db.hunt_chart]
        weights = [e.get("weight", 1) for e in self.db.hunt_chart]
        return random.choices(population, weights=weights, k=1)[0]

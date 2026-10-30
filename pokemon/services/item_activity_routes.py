"""Explicit, idempotent authoring for reviewed training and evolution locations."""

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json


@dataclass(frozen=True)
class ItemActivityRoute:
    """Author a named activity once; imports/startup never install or change a room."""

    key: str
    room_name: str
    entrance: str
    description: str
    attributes: dict

    def recipe(self):
        """Bind exact source identity, public exits and reviewed room attributes."""
        return {"version": 1, "key": self.key, "room": self.room_name,
                "entrance": self.entrance, "return_exit": "back",
                "description": self.description, "attributes": self.attributes}

    def install(self, hub):
        """Require an explicit operator call and preserve all existing objects on drift."""
        from django.db import connection, transaction
        from evennia.objects.models import ObjectDB
        from evennia.utils.create import create_object
        from pokemon.services.battle_rewards import BattleRewards

        recipe = self.recipe()
        fingerprint = hashlib.sha256(json.dumps(recipe, sort_keys=True).encode()).hexdigest()
        marker = "activity_" + self.key
        lock = int.from_bytes(hashlib.sha256(marker.encode()).digest()[:8], "big") >> 1
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_advisory_xact_lock(%s)", [lock])
                hub = ObjectDB.objects.select_for_update().get(pk=hub.pk)
                prior = BattleRewards.stored_attribute(hub, marker)
                existing = list(ObjectDB.objects.filter(db_tags__db_key=self.key,
                                                       db_tags__db_category="item_activity").distinct())
                if prior is not None:
                    if (not isinstance(prior, Mapping) or prior.get("version") != 1
                            or prior.get("recipe_sha256") != fingerprint or len(existing) != 1):
                        raise ValueError("Existing activity source needs review; nothing was overwritten.")
                    room = existing[0]
                    if room.pk != prior.get("room"):
                        raise ValueError("Activity location conflict.")
                    for key, value in self.attributes.items():
                        if BattleRewards.stored_attribute(room, key) != value:
                            raise ValueError("Activity context configuration drift.")
                    for key, location, destination, name in (("entrance", hub, room, self.entrance),
                                                             ("return_exit", room, hub, "back")):
                        exit_row = ObjectDB.objects.filter(pk=prior.get(key), db_location=location,
                                                          db_destination=destination, db_key=name).first()
                        if (exit_row is None or not {"call:all()", "view:all()", "traverse:all()"}
                                <= set(str(exit_row.db_lock_storage).split(";"))):
                            raise ValueError("Activity exits or public access need review.")
                    return room
                if existing or ObjectDB.objects.filter(db_location=hub, db_key__iexact=self.entrance).exists():
                    raise ValueError("An activity source or conflicting entrance already exists.")
                room = create_object("typeclasses.rooms.FusionRoom", key=self.room_name, nohome=True)
                room.tags.add(self.key, category="item_activity")
                room.attributes.add("desc", self.description)
                for key, value in self.attributes.items():
                    room.attributes.add(key, value)
                entrance = create_object("typeclasses.exits.Exit", key=self.entrance,
                                         location=hub, destination=room, nohome=True)
                returning = create_object("typeclasses.exits.Exit", key="back",
                                          location=room, destination=hub, nohome=True)
                for exit_row in (entrance, returning):
                    # Evennia gathers object commands only after the call lock.
                    # Preserve the base exit's call/security locks as well as
                    # making this authored route visible and traversable.
                    exit_row.locks.add("call:all();view:all();traverse:all()")
                hub.attributes.add(marker, {"version": 1, "recipe_sha256": fingerprint,
                                           "room": room.pk, "entrance": entrance.pk,
                                           "return_exit": returning.pk})
                return room
        finally:
            hub.attributes.reset_cache()


TRAINING_GROUNDS = ItemActivityRoute(
    "training-grounds-v1", "Training Grounds", "training",
    "A coaching sign explains +train <target>=<stat>, +train confirm and three active 30-second "
    "exercises for up to 64 EVs. Training and confirmed partial/full retraining are free. "
    "Use +train help for exact caps, timing and earned item milestones. The back exit returns to the hub.",
    {"training_ground": True, "allow_hunting": False, "noitem": True})

TRAINING_TRAIL = ItemActivityRoute(
    "training-trail-v1", "Training Trail", "trainingtrail",
    "A sign invites optional training-supply searches with +hunt. Feathers and EV berries are common "
    "among finds; Candy and Caps are rarer. Use +inventory and +itemdex <item> to inspect. "
    "This practice trail has no wild or NPC battles. The back exit returns to the hub.",
    {"allow_hunting": True, "noitem": False, "itemfinder_profile": "training-v1",
     "itemfinder_rate": 5, "npc_chance": 0, "encounter_rate": 0})

DAY_GROVE = ItemActivityRoute(
    "day-evolution-grove-v1", "Day Grove", "daygrove",
    "This grove supplies a fixed day evolution context. An owned native Happiny holding an Oval "
    "Stone can use +evolve <full ID>. All ordinary ownership, egg, reservation and level guards "
    "apply. Other native day evolutions retain their existing rules. The back exit returns to the hub.",
    {"time_of_day": "day", "allow_hunting": False, "noitem": True})

NIGHT_GROVE = ItemActivityRoute(
    "night-evolution-grove-v1", "Night Grove", "nightgrove",
    "This grove supplies a fixed night evolution context. Native Sneasel holding Razor Claw "
    "can evolve to Weavile; native Gligar holding Razor Fang can evolve to Gliscor. Use +evolve "
    "<full ID>; ordinary guards and native forms apply. The back exit returns to the hub.",
    {"time_of_day": "night", "allow_hunting": False, "noitem": True})

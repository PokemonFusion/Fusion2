"""One optional non-plot Potion finder source with durable claim/cooldown state."""

import time
from collections.abc import Mapping
from math import isfinite
from uuid import uuid4


class ItemfinderClaim:
    """Bind one server-created hunt attempt and serialize its actual bag delivery."""

    key = "itemfinder_receipt"
    cooldown = 3

    def __init__(self, hunter, room, *, clock=time.time, rng=None):
        """Give retries the same internal identity without accepting client tokens."""
        import random

        self.hunter, self.room = hunter, room
        self.clock, self.rng = clock, rng or random
        self.identifier, self.started = str(uuid4()), clock()
        if type(self.started) not in (int, float) or not isfinite(self.started):
            raise ValueError("The server search clock is unavailable.")

    def claim(self):
        """Deliver at most one Potion for this attempt, or return an honest refusal."""
        from django.db import connection, transaction
        from evennia.objects.models import ObjectDB
        from pokemon.models.trainer import Trainer
        from pokemon.names import normalize_name
        from pokemon.services.battle_rewards import BattleRewards
        from pokemon.services.item_shop import ShopPurchase
        from utils.locks import require_no_battle_lock

        if connection.in_atomic_block:
            # Public hunt output cannot be recalled if its enclosing operation
            # later aborts. Refuse before credit/receipt rather than announce a
            # Potion that has not reached an outer commit boundary.
            return "Item searches require a fresh player command; no item was granted."
        character = BattleRewards.character(self.hunter)
        if not BattleRewards.supports(self.hunter):
            return None
        room = None
        try:
            with transaction.atomic():
                character = ObjectDB.objects.select_for_update().get(pk=character.pk)
                position = ObjectDB.objects.filter(pk=character.pk).values_list("db_location_id", flat=True).get()
                room = ObjectDB.objects.get(pk=self.room.pk)
                if position != room.pk or getattr(self.hunter.location, "pk", None) != room.pk:
                    return "You are no longer hunting in that location."
                read = BattleRewards.stored_attribute
                enabled = read(room, "allow_hunting")
                if enabled not in (True, "true", "yes", "1", "on") or read(room, "noitem", default=False):
                    return None
                if normalize_name(read(room, "itemfinder_item", default="")) != "potion":
                    return None
                rate = read(room, "itemfinder_rate", default=0)
                if type(rate) is not int or not 0 <= rate <= 100:
                    return None
                if not require_no_battle_lock(self.hunter):
                    return "You cannot search for items during battle."
                prior = read(character, self.key)
                if prior is not None:
                    if (not isinstance(prior, Mapping) or prior.get("version") != 1
                            or type(prior.get("started")) not in (int, float)
                            or not isfinite(prior["started"])):
                        return "Your finder record needs staff review; no item was granted."
                    if prior.get("attempt") == self.identifier:
                        return "That item search was already completed."
                    if self.started < prior["started"] + self.cooldown:
                        return "You need to wait before searching for items again."
                found = self.rng.randint(1, 100) <= rate
                trainer = Trainer.objects.select_for_update().get(user_id=character.pk)
                if found:
                    trainer.add_item("Potion", 1)
                character.attributes.add(self.key, {"version": 1, "attempt": self.identifier,
                    "started": self.started, "room": room.pk, "item": "Potion" if found else "",
                    "quantity": int(found)})
                return "You found a Potion! It was added to your inventory." if found else None
        finally:
            ShopPurchase.refresh_attributes(character, self.key, "inventory")

"""Named opt-in item sources with durable one-attempt claim/cooldown state."""

import time
from collections.abc import Mapping
from math import isfinite
from uuid import uuid4


class FinderProfile:
    """Keep the original Potion rule and one exact fifteen-name training table."""

    training = (
        ("Health Feather", 8), ("Muscle Feather", 8), ("Resist Feather", 8),
        ("Genius Feather", 8), ("Clever Feather", 8), ("Swift Feather", 8),
        ("Pomeg Berry", 6), ("Kelpsy Berry", 6), ("Qualot Berry", 6),
        ("Hondew Berry", 6), ("Grepa Berry", 6), ("Tamato Berry", 6),
        ("Rare Candy", 12), ("Bottle Cap", 3), ("Gold Bottle Cap", 1),
    )

    @classmethod
    def resolve(cls, room, read):
        """Refuse mixed/unknown room configuration without enabling a fallback table."""
        from pokemon.names import normalize_name

        item = normalize_name(read(room, "itemfinder_item", default=""))
        profile = read(room, "itemfinder_profile", default="")
        rate = read(room, "itemfinder_rate", default=0)
        if profile in (None, ""):
            if item == "potion" and type(rate) is int and 0 <= rate <= 100:
                return "potion", rate, (("Potion", 100),)
        elif profile == "training-v1" and not item and type(rate) is int and rate == 5:
            return profile, rate, cls.training
        return None

    @staticmethod
    def select(weights, rng):
        """Keep legacy Potion's single roll unchanged; training uses one weighted roll."""
        if len(weights) == 1:
            return weights[0][0]
        roll, total = rng.randint(1, 100), 0
        for name, weight in weights:
            total += weight
            if roll <= total:
                return name
        raise ValueError("Invalid reviewed Finder weight table or random source.")


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
        """Deliver at most one named item for this attempt, or an honest refusal."""
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
                profile = FinderProfile.resolve(room, read)
                if profile is None:
                    return None
                profile_name, rate, weights = profile
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
                item = FinderProfile.select(weights, self.rng) if found else ""
                if found:
                    if trainer.add_item(item, 1) is False:
                        raise ValueError("The Finder item could not be saved.")
                character.attributes.add(self.key, {"version": 1, "attempt": self.identifier,
                    "started": self.started, "room": room.pk, "item": item,
                    "quantity": int(found), "profile": profile_name})
                return f"You found a {item}! It was added to your inventory." if found else None
        finally:
            ShopPurchase.refresh_attributes(character, self.key, "inventory")

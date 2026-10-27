"""Explicit duplicate-safe finite counters for reviewed item feature slices."""

from dataclasses import dataclass
from collections.abc import Mapping
import hashlib
import json
from pathlib import Path


@dataclass(frozen=True)
class ItemCounter:
    """Install a checked-in recipe only when an operator selects an actual hub."""

    recipe_path: str

    def recipe(self):
        """Reject malformed content before any room, exit or stock write."""
        from pokemon.middleware import get_item_by_name

        path = Path(__file__).resolve().parents[2] / self.recipe_path
        data = json.loads(path.read_text(encoding="utf-8"))
        offers = data.get("offers", [])
        if (data.get("version") != 1 or data.get("refill") != "none"
                or data.get("buy_only") is not True or not offers
                or len({o["item"] for o in offers}) != len(offers)
                or not all(data.get(k) for k in ("key", "room", "entrance", "return_exit", "description"))):
            raise ValueError("Invalid reviewed item counter recipe.")
        for offer in offers:
            if (type(offer.get("price")) is not int or offer["price"] <= 0
                    or type(offer.get("quantity")) is not int or offer["quantity"] <= 0
                    or get_item_by_name(offer["item"])[1] is None):
                raise ValueError("Invalid item counter offer.")
        return data

    def install(self, hub):
        """Author once and discard tentative marker caches after outer rollback."""
        from django.db import connection, transaction
        from pokemon.services.item_shop import ShopPurchase

        data = self.recipe()
        marker = "counter_" + data["key"]
        hub.attributes.reset_cache()
        try:
            return self._install(hub, data)
        finally:
            hub.attributes.reset_cache()
            if connection.in_atomic_block:
                transaction.on_commit(lambda: ShopPurchase.refresh_attributes(hub, marker), robust=True)
            else:
                ShopPurchase.refresh_attributes(hub, marker)

    def _install(self, hub, data):
        """Atomically author one validated source, never replenish an existing one."""
        from django.db import connection, transaction
        from evennia.objects.models import ObjectDB
        from evennia.utils.create import create_object
        from pokemon.services.battle_rewards import BattleRewards

        marker = "counter_" + data["key"]
        lock = int.from_bytes(hashlib.sha256(data["key"].encode()).digest()[:8], "big") >> 1
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", [lock])
            hub = ObjectDB.objects.select_for_update().get(pk=hub.pk)
            prior = BattleRewards.stored_attribute(hub, marker)
            existing = list(ObjectDB.objects.filter(db_tags__db_key=data["key"],
                                                    db_tags__db_category="item_counter").distinct())
            if prior is not None:
                if not isinstance(prior, Mapping) or prior.get("version") != 1 or len(existing) != 1:
                    raise ValueError("Existing counter setup requires review.")
                room = existing[0]
                if room.pk != prior.get("room"):
                    raise ValueError("Counter room conflict; nothing was overwritten.")
                if not ObjectDB.objects.filter(pk=prior.get("entrance"), db_location=hub,
                                               db_destination=room, db_key=data["entrance"]).exists():
                    raise ValueError("Counter entrance conflict; nothing was overwritten.")
                if not ObjectDB.objects.filter(pk=prior.get("return_exit"), db_location=room,
                                               db_destination=hub, db_key=data["return_exit"]).exists():
                    raise ValueError("Counter return conflict; nothing was overwritten.")
                stock = BattleRewards.stored_attribute(room, "store_inventory", default={})
                if (BattleRewards.stored_attribute(room, "is_item_shop") is not True
                        or BattleRewards.stored_attribute(room, "store_buy_only") is not True
                        or set(stock) != {offer["item"] for offer in data["offers"]}):
                    raise ValueError("Counter policy/stock drift; nothing was reset.")
                for offer in data["offers"]:
                    current = stock[offer["item"]]
                    if (current.get("price") != offer["price"] or type(current.get("quantity")) is not int
                            or not 0 <= current["quantity"] <= offer["quantity"]):
                        raise ValueError("Counter stock drift; nothing was reset.")
                for key, value in data.get("room_attributes", {}).items():
                    if BattleRewards.stored_attribute(room, key) != value:
                        raise ValueError("Counter source configuration drift.")
                return room
            if existing or ObjectDB.objects.filter(db_location=hub, db_key__iexact=data["entrance"]).exists():
                raise ValueError("An item counter or conflicting exit already exists.")
            room = create_object("typeclasses.rooms.FusionRoom", key=data["room"], nohome=True)
            room.tags.add(data["key"], category="item_counter")
            room.db.desc = data["description"]
            room.db.is_item_shop, room.db.store_buy_only = True, True
            room.db.noitem, room.db.allow_hunting = True, False
            room.db.store_inventory = {o["item"]: {"price": o["price"], "quantity": o["quantity"]}
                                       for o in data["offers"]}
            for key, value in data.get("room_attributes", {}).items():
                if key not in {"berry_nursery"} or type(value) is not bool:
                    raise ValueError("Unreviewed room attribute in counter recipe.")
                room.attributes.add(key, value)
            entrance = create_object("typeclasses.exits.Exit", key=data["entrance"], location=hub,
                                     destination=room, nohome=True)
            returning = create_object("typeclasses.exits.Exit", key=data["return_exit"], location=room,
                                      destination=hub, nohome=True)
            hub.attributes.add(marker, {"version": 1, "room": room.pk,
                                       "entrance": entrance.pk, "return_exit": returning.pk})
            return room


class BerryNursery:
    """The two-offer nursery remains independent of the six-item Supply Corner."""

    @staticmethod
    def install(hub):
        """Install only at the explicitly supplied, reviewed hub."""
        return ItemCounter("world/berry_nursery.json").install(hub)

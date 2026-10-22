"""Explicit opt-in, duplicate-safe authoring for one small item supply location."""

import json
from collections.abc import Mapping
from pathlib import Path


class ItemSupplyRoute:
    """Install once at an explicitly selected public hub, never at server startup."""

    key = "nonplot-item-supply-v1"
    marker = "item_supply_route"
    names = {"Potion", "Oran Berry", "Fresh Water", "Fire Stone", "Leftovers", "Smoke Ball"}

    @classmethod
    def recipe(cls):
        """Validate the exact six-offer authored slice before any world write."""
        from pokemon.middleware import get_item_by_name

        path = Path(__file__).resolve().parents[2] / "world/item_supply.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        offers = data.get("offers", [])
        if (data.get("version") != 1 or data.get("key") != cls.key or data.get("refill") != "none"
                or data.get("buy_only") is not True or len(offers) != 6
                or {offer.get("item") for offer in offers} != cls.names):
            raise ValueError("The supply recipe requires a new review.")
        for offer in offers:
            if (type(offer.get("price")) is not int or offer["price"] <= 0
                    or type(offer.get("quantity")) is not int or offer["quantity"] <= 0
                    or get_item_by_name(offer["item"])[1] is None):
                raise ValueError("Invalid supply offer.")
        return data

    @classmethod
    def install(cls, hub):
        """Run only from explicit builder setup; repeated installs never refill stock."""
        from django.db import connection, transaction
        from evennia.utils.create import create_object
        from evennia.objects.models import ObjectDB
        from pokemon.services.battle_rewards import BattleRewards

        data = cls.recipe()
        with transaction.atomic():
            # Serialize the single route even if two staff requests name different hubs.
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", [78120261022])
            hub = ObjectDB.objects.select_for_update().get(pk=hub.pk)
            prior = BattleRewards.stored_attribute(hub, cls.marker)
            existing = list(ObjectDB.objects.filter(db_tags__db_key=cls.key,
                                                    db_tags__db_category="item_supply").distinct())
            if prior is not None:
                if not isinstance(prior, Mapping) or prior.get("version") != 1 or len(existing) != 1:
                    raise ValueError("Existing supply setup needs review; nothing was overwritten.")
                room = existing[0]
                if room.pk != prior.get("room"):
                    raise ValueError("Supply location conflict; nothing was overwritten.")
                entrance = ObjectDB.objects.filter(pk=prior.get("entrance"), db_location=hub,
                                                   db_destination=room, db_key=data["entrance"]).first()
                returning = ObjectDB.objects.filter(pk=prior.get("return_exit"), db_location=room,
                                                    db_destination=hub, db_key=data["return_exit"]).first()
                if not entrance or not returning:
                    raise ValueError("Supply exits need review; no duplicate exits were created.")
                offers = BattleRewards.stored_attribute(room, "store_inventory", default={})
                if (BattleRewards.stored_attribute(room, "is_item_shop") is not True
                        or BattleRewards.stored_attribute(room, "store_buy_only") is not True
                        or not isinstance(offers, Mapping) or set(offers) != cls.names):
                    raise ValueError("Supply configuration needs review; stock was not reset.")
                for offer in data["offers"]:
                    current = offers[offer["item"]]
                    if (current.get("price") != offer["price"] or type(current.get("quantity")) is not int
                            or not 0 <= current["quantity"] <= offer["quantity"]):
                        raise ValueError("Supply offer drift needs review; stock was not reset.")
                return room
            if existing or ObjectDB.objects.filter(db_location=hub, db_key__iexact=data["entrance"]).exists():
                raise ValueError("A supply route or conflicting entrance already exists.")
            room = create_object("typeclasses.rooms.FusionRoom", key=data["room"], nohome=True)
            room.tags.add(cls.key, category="item_supply")
            room.db.desc = ("A sign lists six non-plot supplies: Potion, Oran Berry, Fresh Water, "
                            "Fire Stone, Leftovers and Smoke Ball. Use +store to buy finite stock. "
                            "Use +inventory and +itemdex <item>; +use feeds medicine/berries/food, "
                            "+evolve <full-id> Fire Stone evolves an eligible Pokemon, and +hold "
                            "equips reusable items. Smoke Ball uses +flee in an eligible wild battle. "
                            "The back exit returns to the hub. There is no automatic refill or resale.")
            room.db.is_item_shop, room.db.store_buy_only = True, True
            room.db.allow_hunting, room.db.noitem = False, True
            room.db.store_inventory = {offer["item"]: {"price": offer["price"], "quantity": offer["quantity"]}
                                       for offer in data["offers"]}
            entrance = create_object("typeclasses.exits.Exit", key=data["entrance"], location=hub, destination=room, nohome=True)
            returning = create_object("typeclasses.exits.Exit", key=data["return_exit"], location=room, destination=hub, nohome=True)
            hub.attributes.add(cls.marker, {"version": 1, "room": room.pk,
                                           "entrance": entrance.pk, "return_exit": returning.pk})
            return room

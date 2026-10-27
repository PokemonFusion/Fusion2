"""Atomic purchases for persistent ordinary item-shop customers."""

from collections.abc import Mapping


class ShopPurchaseError(ValueError):
    """A purchase was refused without committing stock, money or inventory."""


class ShopPurchase:
    """Serialize room stock, then the buyer's trainer/inventory in one transaction."""

    def __init__(self, caller):
        """Bind the current customer and room rather than a stale menu offer."""
        self.caller = caller
        self.room = caller.location

    @staticmethod
    def supports(caller):
        """Keep nonpersistent menu simulations separate from production commerce."""
        from pokemon.services.battle_rewards import BattleRewards

        return BattleRewards.supports(caller)

    @staticmethod
    def refresh_attributes(owner, *keys):
        """Discard uncommitted Attribute values without rewriting any database row."""
        from evennia.typeclasses.models import Attribute

        for row in owner.db_attributes.filter(db_key__in=keys, db_category=None).values("pk", "db_value"):
            attribute = Attribute.objects.get(pk=row["pk"])
            attribute.db_value = row["db_value"]
            Attribute.cache_instance(attribute)
        owner.attributes.reset_cache()

    @staticmethod
    def write_stock(room, store):
        """Update existing stock SQL without publishing an uncommitted shared Attribute."""
        from evennia.utils.dbserialize import to_pickle

        changed = room.db_attributes.filter(db_key="store_inventory", db_category=None,
                                            db_attrtype=None).update(db_value=to_pickle(store))
        if changed != 1:
            raise ShopPurchaseError("The store inventory is unavailable.")

    def buy(self, name, amount):
        """Commit one fresh finite-stock purchase, or leave every resource unchanged."""
        from django.db import connection, transaction
        from evennia.objects.models import ObjectDB
        from pokemon.models.trainer import Trainer
        from pokemon.services.battle_rewards import BattleRewards

        if type(amount) is not int or amount <= 0:
            raise ShopPurchaseError("You must purchase a positive whole number of items.")
        room = self.room
        if room is None or not getattr(room, "pk", None):
            raise ShopPurchaseError("There is no store here.")
        try:
            with transaction.atomic():
                room = ObjectDB.objects.select_for_update().get(pk=room.pk)
                if (getattr(self.caller.location, "pk", None) != room.pk
                        or BattleRewards.stored_attribute(room, "is_item_shop") is not True):
                    raise ShopPurchaseError("There is no store here.")
                raw = BattleRewards.stored_attribute(room, "store_inventory", default={})
                if not isinstance(raw, Mapping):
                    raise ShopPurchaseError("The store inventory is unavailable.")
                matches = [key for key in raw if isinstance(key, str) and key.casefold() == name.casefold()]
                if len(matches) != 1 or not isinstance(raw[matches[0]], Mapping):
                    raise ShopPurchaseError("The store doesn't have that many.")
                key, offer = matches[0], raw[matches[0]]
                price, quantity = offer.get("price"), offer.get("quantity")
                if type(price) is not int or price < 0 or type(quantity) is not int or quantity < 0:
                    raise ShopPurchaseError("The store offer is unavailable.")
                if quantity < amount:
                    raise ShopPurchaseError("The store doesn't have that many.")
                trainer = Trainer.objects.select_for_update().get(user_id=self.caller.pk)
                if not trainer.spend_money(price * amount):
                    raise ShopPurchaseError("You can't afford that.")
                trainer.add_item(key, amount)
                store = {item: dict(value) if isinstance(value, Mapping) else value for item, value in raw.items()}
                store[key] = {**dict(offer), "quantity": quantity - amount}
                self.write_stock(room, store)
                message = f"You purchase {amount} x {key} for ${price * amount}."

                def publish():
                    """Publish inventory/currency state and success only after outer commit."""
                    self.caller.trainer.money = trainer.money
                    self.caller.msg(message)

                transaction.on_commit(publish, robust=True)
        except (ObjectDB.DoesNotExist, Trainer.DoesNotExist) as error:
            raise ShopPurchaseError("The store or customer is no longer available.") from error
        finally:
            if not hasattr(room, "db_attributes"):
                pass
            elif connection.in_atomic_block:
                # Shared handlers must not retain values from a containing transaction.
                room.attributes.reset_cache()
                transaction.on_commit(lambda: self.refresh_attributes(room, "store_inventory"), robust=True)
            else:
                self.refresh_attributes(room, "store_inventory")

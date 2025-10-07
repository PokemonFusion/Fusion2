"""Typeclasses for in-world vending machines."""

from __future__ import annotations

from .objects import Object


class PokeballVendor(Object):
    """Simple machine that dispenses Poké Balls when used."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.dispense_item = self.db.dispense_item or "Pokeball"
        self.db.dispense_quantity = self.db.dispense_quantity or 1
        self.db.stock = self.db.stock if self.db.stock is not None else None
        self.db.desc = self.db.desc or "A cheerful vending machine stocked with Poké Balls."

    def vend_item(self, caller, amount: int = 1) -> bool:
        """Dispense ``amount`` bundles of the configured item to ``caller``."""

        if amount <= 0:
            caller.msg("The machine blinks red. Maybe try a positive number?")
            return False

        item_name = self.db.dispense_item or "Pokeball"
        per_vend = max(1, int(self.db.dispense_quantity or 1))
        total = per_vend * amount

        stock = self.db.stock
        if isinstance(stock, int):
            if stock < total:
                caller.msg("The vending machine is out of stock.")
                return False
            self.db.stock = stock - total

        if not hasattr(caller, "add_item"):
            caller.msg("You have no way to carry the dispensed item.")
            return False

        caller.add_item(item_name, total)
        caller.msg(f"{self.key} dispenses {total} x {item_name}.")
        location = getattr(self, "location", None)
        if location:
            location.msg_contents(
                f"{caller.key} receives {total} x {item_name} from {self.key}.", exclude=caller
            )
        return True

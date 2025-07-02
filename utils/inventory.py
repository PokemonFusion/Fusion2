class InventoryMixin:
    """Mixin providing simple inventory management."""

    @property
    def inventory(self):
        """Return inventory dictionary mapping item names to counts."""
        inv = getattr(self.db, "inventory", None)
        if inv is None:
            inv = {}
            self.db.inventory = inv
        return inv

    def add_item(self, name: str, quantity: int = 1) -> None:
        inv = self.inventory
        inv[name] = inv.get(name, 0) + quantity
        self.db.inventory = inv

    def remove_item(self, name: str, quantity: int = 1) -> bool:
        inv = self.inventory
        if inv.get(name, 0) < quantity:
            return False
        inv[name] -= quantity
        if inv[name] <= 0:
            del inv[name]
        self.db.inventory = inv
        return True

    def has_item(self, name: str, quantity: int = 1) -> bool:
        return self.inventory.get(name, 0) >= quantity

    def list_inventory(self) -> str:
        inv = self.inventory
        if not inv:
            return "You have no items."
        lines = [f"{item} x{amount}" for item, amount in inv.items()]
        return "\n".join(lines)


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


def add_item(trainer, item_name: str, amount: int = 1):
    """Add ``amount`` of ``item_name`` to ``trainer``'s inventory."""
    from pokemon.models import InventoryEntry

    item_name = item_name.lower()
    entry, _ = InventoryEntry.objects.get_or_create(
        owner=trainer, item_name=item_name, defaults={"quantity": 0}
    )
    entry.quantity += amount
    entry.save()


def remove_item(trainer, item_name: str, amount: int = 1) -> bool:
    """Remove ``amount`` of ``item_name`` from ``trainer``. Return success."""
    from pokemon.models import InventoryEntry

    item_name = item_name.lower()
    try:
        entry = InventoryEntry.objects.get(owner=trainer, item_name=item_name)
    except InventoryEntry.DoesNotExist:
        return False
    if entry.quantity < amount:
        return False
    entry.quantity -= amount
    if entry.quantity <= 0:
        entry.delete()
    else:
        entry.save()
    return True


def get_inventory(trainer):
    """Return ``InventoryEntry`` objects owned by ``trainer`` ordered by item."""
    from pokemon.models import InventoryEntry

    return InventoryEntry.objects.filter(owner=trainer).order_by("item_name")


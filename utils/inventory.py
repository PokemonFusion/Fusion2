class Inventory:
    """Container storing item counts and providing utility helpers."""

    def __init__(self, store=None):
        self.store = store or {}

    # Basic mapping helpers -------------------------------------------------
    def __getitem__(self, key):
        return self.store[key]

    def __setitem__(self, key, value):
        self.store[key] = value

    def __contains__(self, key):
        return key in self.store

    def get(self, key, default=None):
        return self.store.get(key, default)

    def items(self):
        return self.store.items()

    # Inventory operations --------------------------------------------------
    def add(self, name: str, quantity: int = 1) -> None:
        self.store[name] = self.store.get(name, 0) + quantity

    def remove(self, name: str, quantity: int = 1) -> bool:
        if self.store.get(name, 0) < quantity:
            return False
        self.store[name] -= quantity
        if self.store[name] <= 0:
            del self.store[name]
        return True

    def has(self, name: str, quantity: int = 1) -> bool:
        return self.store.get(name, 0) >= quantity

    def list(self) -> str:
        if not self.store:
            return "You have no items."
        lines = [f"{item} x{amount}" for item, amount in self.store.items()]
        return "\n".join(lines)


class InventoryMixin:
    """Mixin providing simple inventory management."""

    @property
    def inventory(self) -> Inventory:
        """Return the :class:`Inventory` for this object."""
        inv = getattr(self.db, "inventory", None)
        if inv is None:
            inv = Inventory()
            self.db.inventory = inv
        elif isinstance(inv, dict):
            inv = Inventory(inv)
            self.db.inventory = inv
        return inv

    # Delegate helper methods to the :class:`Inventory` instance -------------
    def add_item(self, name: str, quantity: int = 1) -> None:
        self.inventory.add(name, quantity)

    def remove_item(self, name: str, quantity: int = 1) -> bool:
        return self.inventory.remove(name, quantity)

    def has_item(self, name: str, quantity: int = 1) -> bool:
        return self.inventory.has(name, quantity)

    def list_inventory(self) -> str:
        return self.inventory.list()


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


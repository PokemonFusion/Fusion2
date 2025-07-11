import os
import types
import sys
import importlib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class FakeInvManager:
    def __init__(self):
        self.store = {}

    def get_or_create(self, owner=None, item_name=None, **kwargs):
        key = (owner, item_name)
        if key not in self.store:
            entry = FakeInventoryEntry(owner, item_name)
            self.store[key] = entry
            created = True
        else:
            entry = self.store[key]
            created = False
        return entry, created

    def get(self, owner=None, item_name=None, **kwargs):
        key = (owner, item_name)
        if key not in self.store:
            raise FakeInventoryEntry.DoesNotExist
        return self.store[key]

    def filter(self, owner=None, **kwargs):
        items = [e for e in self.store.values() if owner is None or e.owner == owner]

        class _QS(list):
            def order_by(self_inner, field):
                return sorted(self_inner, key=lambda x: getattr(x, field))

        return _QS(items)


class FakeInventoryEntry:
    objects = FakeInvManager()

    class DoesNotExist(Exception):
        pass

    def __init__(self, owner, item_name, quantity=0):
        self.owner = owner
        self.item_name = item_name
        self.quantity = quantity

    def save(self):
        FakeInventoryEntry.objects.store[(self.owner, self.item_name)] = self

    def delete(self):
        FakeInventoryEntry.objects.store.pop((self.owner, self.item_name), None)


models_mod = types.ModuleType("pokemon.models")
models_mod.InventoryEntry = FakeInventoryEntry
sys.modules["pokemon.models"] = models_mod

inv_mod = importlib.import_module("utils.inventory")
InventoryMixin = inv_mod.InventoryMixin

class Dummy(InventoryMixin):
    def __init__(self):
        self.db = types.SimpleNamespace()
        self.db.inventory = {}


def test_add_and_remove_item():
    d = Dummy()
    d.add_item("Potion", 2)
    assert d.has_item("Potion")
    assert d.inventory["Potion"] == 2
    d.remove_item("Potion")
    assert d.inventory["Potion"] == 1
    d.remove_item("Potion")
    assert "Potion" not in d.inventory


def test_list_inventory_empty():
    d = Dummy()
    assert d.list_inventory() == "You have no items."
    d.add_item("Potion")
    assert "Potion" in d.list_inventory()


def test_inventory_functions():
    trainer = object()
    inv_mod.add_item(trainer, "potion", 2)
    inv_mod.add_item(trainer, "potion")
    assert any(e.item_name == "potion" and e.quantity == 3 for e in inv_mod.get_inventory(trainer))
    assert inv_mod.remove_item(trainer, "potion", 2)
    assert any(e.quantity == 1 for e in inv_mod.get_inventory(trainer))
    assert inv_mod.remove_item(trainer, "potion", 1)
    assert list(inv_mod.get_inventory(trainer)) == []


def test_add_various_medicines():
    d = Dummy()
    meds = [
        "Antidote",
        "Revive",
        "Ether",
        "Ability Capsule",
    ]
    for item in meds:
        d.add_item(item)
    listed = d.list_inventory()
    for item in meds:
        assert item in listed


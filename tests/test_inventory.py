import os
import types
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.inventory import InventoryMixin

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


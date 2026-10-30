"""The selected food/drink/revival table has exact identities and useful metadata."""

import csv
from pathlib import Path
from types import SimpleNamespace

import pytest

from pokemon.items import BATTLE_RECOVERY_FOODS, FIELD_RECOVERY_ITEMS, get_gameplay_item
from pokemon.middleware import format_item_details, get_item_by_name
from pokemon.names import normalize_name


@pytest.mark.parametrize("key,item", FIELD_RECOVERY_ITEMS.items())
def test_complete_names_costs_categories_and_context_are_exposed(key, item):
    """Reference prices match the local source; no prefix or plot rule is added."""
    source = Path(__file__).resolve().parents[2] / "pokemon/data/item_prices.csv"
    with source.open(newline="", encoding="utf-8") as stream:
        row = next(row for row in csv.DictReader(stream) if normalize_name(row["identifier"]) == key)
    assert item.price == int(row["cost"])
    for query in (item.name, key, item.name.upper().replace(" ", "-")):
        assert get_gameplay_item(query) is item
        assert get_item_by_name(query)[1] is item
    details = format_item_details(key, item)
    assert "Category: Medicine" in details
    assert f"Reference price: ${item.price}" in details
    assert item.desc in details
    assert item.raw["fieldOnly"] is (key not in BATTLE_RECOVERY_FOODS)
    assert item.target_scope == ("party" if key == "sacredash" else "single")


@pytest.mark.parametrize("query", ["Fresh", "Soda", "Milk", "Sweet", "Cookie", "Honey", "Sacred", "Max Soup"])
def test_partial_names_and_unrelated_transformation_items_remain_unknown(query):
    """No partial match can select one of the new recovery items."""
    assert get_item_by_name(query) == (None, None)


@pytest.mark.parametrize("key,item", FIELD_RECOVERY_ITEMS.items())
def test_shared_effects_are_useful_capped_and_consume_once(key, item):
    """All fourteen definitions dispatch through the real shared medicine effect."""
    from pokemon.services.battle_items import BattleMedicineUse
    from pokemon.services.field_food import FieldFoodUse, _FoodMedicineUse

    hp = 0 if item.effect == "revive" else 1
    target = SimpleNamespace(hp=hp, max_hp=80, status="slp", friendship=137, model_id=None)
    target.setStatus = lambda value, **kwargs: setattr(target, "status", value)
    debits = []
    assert FieldFoodUse.supports(key)
    assert BattleMedicineUse.supports(key) is (key in BATTLE_RECOVERY_FOODS)
    assert _FoodMedicineUse(target).use(key, lambda: debits.append(key) or True)
    assert debits == [key]
    assert target.hp == (min(80, 1 + item.amount) if item.effect == "heal" else 80 if item.effect == "revive" else 1)
    assert target.status == (0 if item.effect == "status" else "slp")
    assert target.friendship == 137
    if item.effect != "heal":
        assert not _FoodMedicineUse(target).use(key, lambda: debits.append(key) or True)
        assert debits == [key]

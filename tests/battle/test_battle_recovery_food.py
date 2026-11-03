"""Keep the reviewed battle recovery boundary independent of field/held effects."""

from types import SimpleNamespace

import pytest

from pokemon.items import BATTLE_RECOVERY_FOODS, FIELD_RECOVERY_ITEMS
from pokemon.services.battle_items import BattleItemCapability, BattleMedicineUse
from pokemon.services.field_berries import FieldBerryUse, _BerryMedicineUse
from pokemon.services.field_food import FieldFoodUse
from pokemon.services.field_items import FieldMedicineUse
from pokemon.services.recovery_effects import BERRY_HEALING, BERRY_PP, BERRY_STATUSES


NEW_ITEMS = sorted(BATTLE_RECOVERY_FOODS | BERRY_HEALING.keys() | BERRY_PP.keys()
                   | BERRY_STATUSES.keys() | {"sitrusberry"})


@pytest.mark.parametrize("item", NEW_ITEMS)
def test_named_recovery_items_keep_specialized_field_dispatch(item):
    """Allowlisting battle feeding must not capture broader field feeding routes."""
    assert BattleMedicineUse.supports(item)
    BattleItemCapability.validate(item)
    assert not FieldMedicineUse.supports(item)
    assert (FieldFoodUse if item in BATTLE_RECOVERY_FOODS else FieldBerryUse).supports(item)


@pytest.mark.parametrize("item", ["sacredash", "figyberry", "wikiberry", "magoberry",
    "aguavberry", "iapapaberry", "pomegberry", "kelpsyberry", "qualotberry", "hondewberry",
    "grepaberry", "tamatoberry", "persimberry", "bitterberry", "razzberry", "lansatberry"])
def test_field_and_held_only_items_remain_battle_rejected(item):
    """A berry suffix or a shared field superclass never grants battle capability."""
    assert not BattleMedicineUse.supports(item)
    with pytest.raises(ValueError, match="supported manual battle"):
        BattleItemCapability.validate(item)


def test_fractional_healing_is_per_target_and_field_flavors_remain_distinct():
    """Two differently sized targets cannot overwrite each other's Sitrus cap."""
    small = SimpleNamespace(max_hp=3)
    large = SimpleNamespace(max_hp=199)
    first, second = BattleMedicineUse(small), BattleMedicineUse(large)
    assert first.healing["sitrusberry"] == 1
    assert second.healing["sitrusberry"] == 49
    assert "figyberry" not in first.healing
    assert _BerryMedicineUse(large).healing["figyberry"] == 66
    assert "sitrusberry" not in BattleMedicineUse.healing


def test_food_metadata_reports_the_same_named_battle_boundary():
    """Inventory/dex metadata no longer labels enabled foods field-only."""
    assert len(NEW_ITEMS) == 32
    assert len(BATTLE_RECOVERY_FOODS) == 13
    for key, item in FIELD_RECOVERY_ITEMS.items():
        assert item.raw["fieldOnly"] is (key not in BATTLE_RECOVERY_FOODS)

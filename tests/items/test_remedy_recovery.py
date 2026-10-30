"""Four named field equivalents retain useful-only HP/status and bitter costs."""

from types import SimpleNamespace

import pytest

from pokemon.items import FIELD_RECOVERY_EQUIVALENTS
from pokemon.services.field_recovery_equivalents import _EquivalentMedicineUse


REMEDIES = (("Remedy", 20, (5, 10)), ("Fine Remedy", 60, (10, 15)),
            ("Superb Remedy", 120, (15, 20)))


@pytest.mark.parametrize("item,amount,cost", REMEDIES)
@pytest.mark.parametrize("friendship", (0, 4, 137, 199, 200, 255))
def test_remedy_actual_hp_and_friendship_tiers(item, amount, cost, friendship):
    """A useful capped heal consumes once and applies the correct pre-use tier."""
    target = SimpleNamespace(hp=10, max_hp=200, status="psn", friendship=friendship, model_id=None)
    used = []
    assert _EquivalentMedicineUse(target).use(item, lambda: used.append(1) or True)
    assert target.hp == min(200, 10 + amount)
    assert target.status == "psn" and target.friendship == max(0, friendship - cost[friendship >= 200])
    assert used == [1]


@pytest.mark.parametrize("item,amount,cost", REMEDIES)
@pytest.mark.parametrize("hp", (0, 200))
def test_remedy_no_effect_keeps_stock_and_friendship(item, amount, cost, hp):
    """Fainted and healthy recipients never pay a bitter-medicine penalty."""
    target = SimpleNamespace(hp=hp, max_hp=200, status="", friendship=200, model_id=None)
    used = []
    assert not _EquivalentMedicineUse(target).use(item, lambda: used.append(1) or True)
    assert target.hp == hp and target.friendship == 200 and used == []


@pytest.mark.parametrize("status", ("psn", "tox", "brn", "par", "slp", "frz"))
def test_jubilife_muffin_major_cure_preserves_hp_friendship_and_no_effect_copy(status):
    """The named food inherits the exact shared major-status cure contract."""
    target = SimpleNamespace(hp=10, max_hp=200, status=status, friendship=137, model_id=None)
    target.setStatus = lambda value, **kwargs: setattr(target, "status", value)
    used = []
    assert _EquivalentMedicineUse(target).use("Jubilife Muffin", lambda: used.append(1) or True)
    assert (target.hp, target.status, target.friendship) == (10, 0, 137)
    assert not _EquivalentMedicineUse(target).use("Jubilife Muffin", lambda: used.append(1) or True)
    assert used == [1]


def test_only_new_remedies_add_bitter_metadata():
    """The pre-existing supplemental definitions retain their raw fingerprints."""
    assert "friendshipCost" not in FIELD_RECOVERY_EQUIVALENTS["ragecandybar"].raw
    assert "friendshipCost" not in FIELD_RECOVERY_EQUIVALENTS["hopoberry"].raw
    assert FIELD_RECOVERY_EQUIVALENTS["superbremedy"].raw["friendshipCost"] == [15, 20]

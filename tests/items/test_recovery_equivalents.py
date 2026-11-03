"""Exact field-only capabilities and real status effects for two supplemental items."""

from types import SimpleNamespace

import pytest

from pokemon.items import FIELD_RECOVERY_EQUIVALENTS, get_gameplay_item
from pokemon.services.battle_items import BattleItemCapability, BattleMedicineUse
from pokemon.services.field_recovery_equivalents import FieldRecoveryEquivalentUse, _EquivalentMedicineUse


@pytest.mark.parametrize("key,item", FIELD_RECOVERY_EQUIVALENTS.items())
def test_complete_definition_and_field_only_boundary(key, item):
    """Names/categories describe deliberate field support without manual battle use."""
    assert get_gameplay_item(item.name.upper().replace(" ", "-")) is item
    assert FieldRecoveryEquivalentUse.supports(key)
    assert item.raw["fieldOnly"] is True
    assert not BattleMedicineUse.supports(key)
    with pytest.raises(ValueError):
        BattleItemCapability.validate(item.name)


@pytest.mark.parametrize("status", ["brn", "psn", "tox", "frz", "slp", "par"])
def test_rage_candy_major_cure_has_no_hp_or_friendship_side_effect(status):
    """The shared medicine consumer cures once and a repeat has no useful effect."""
    target = SimpleNamespace(hp=12, max_hp=80, status=status, friendship=137, model_id=None)
    target.setStatus = lambda value, **kwargs: setattr(target, "status", value)
    debit = []
    assert _EquivalentMedicineUse(target).use("Rage Candy Bar", lambda: debit.append(1) or True)
    assert (target.hp, target.status, target.friendship) == (12, 0, 137)
    assert not _EquivalentMedicineUse(target).use("Rage Candy Bar", lambda: debit.append(1) or True)
    assert debit == [1]


@pytest.mark.parametrize("name", ["Rage", "Hopo", "Hopo Juice", "Razz Berry"])
def test_no_prefix_or_unreviewed_flavor_definition(name):
    """A flavor/berry name cannot widen the field allowlist."""
    assert not FieldRecoveryEquivalentUse.supports(name)

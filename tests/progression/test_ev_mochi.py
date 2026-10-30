"""Bind exactly seven field-only mochi to the accepted EV contract."""

import pytest

from pokemon.items import FIELD_TRAINING_ITEMS
from pokemon.services.battle_items import BattleItemCapability
from pokemon.services.field_training import FieldTrainingUse


@pytest.mark.parametrize(
    "name,stat",
    [
        ("Health Mochi", "HP"),
        ("Muscle Mochi", "Attack"),
        ("Resist Mochi", "Defense"),
        ("Genius Mochi", "Special Attack"),
        ("Clever Mochi", "Special Defense"),
        ("Swift Mochi", "Speed"),
        ("Fresh-Start Mochi", None),
    ],
)
def test_exact_mochi_metadata_field_support_and_battle_refusal(name, stat):
    """Definitions describe real field effects without promising a held/manual use."""
    from pokemon.names import normalize_name

    item = FIELD_TRAINING_ITEMS[normalize_name(name)]
    assert item.name == name and item.raw["stat"] == stat
    assert item.raw["fieldOnly"] is True
    assert item.raw["amount"] == (10 if stat else None)
    assert item.raw["price"] == (10000 if stat else 20000)
    assert FieldTrainingUse.supports(name)
    with pytest.raises(ValueError):
        BattleItemCapability.validate(name)


@pytest.mark.parametrize(
    "name", ["Mochi", "Health", "Fresh Start", "Health Mochi 2", "Pretty Feather"]
)
def test_no_broad_mochi_or_training_fallback(name):
    """Prefixes and decorative feathers do not acquire a training effect."""
    assert not FieldTrainingUse.supports(name)


@pytest.mark.parametrize(
    "item,value",
    [("Health Mochi", True), ("Fresh-Start Mochi", True), ("Fresh-Start Mochi", False)],
)
def test_training_rejects_boolean_evs_before_any_debit(item, value):
    """Python bools must not masquerade as saved integer training values."""
    from types import SimpleNamespace
    from pokemon.services.field_items import FieldMedicineError

    pokemon = SimpleNamespace(evs=[value, 0, 0, 0, 0, 0], _state=SimpleNamespace())
    with pytest.raises(FieldMedicineError):
        FieldTrainingUse(None)._apply(item, pokemon, object())
    assert pokemon.evs == [value, 0, 0, 0, 0, 0]

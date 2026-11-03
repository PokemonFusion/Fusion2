"""Exact EXP Candy amounts, strict saved progression and bounded growth policy."""

from types import SimpleNamespace

import pytest

from pokemon.items import EXP_CANDY_ITEMS
from pokemon.services.exp_candy import CandyProgression, FieldExpCandyUse
from pokemon.services.field_items import FieldMedicineError


@pytest.mark.parametrize(
    "size,amount", [("XS", 100), ("S", 800), ("M", 3000), ("L", 10000), ("XL", 30000)]
)
def test_five_exact_candies_share_metadata_and_use_amount(size, amount):
    """One selected copy grants its exact useful amount, not a level increment."""
    key = "expcandy" + size.lower()
    item = EXP_CANDY_ITEMS[key]
    assert item.name == "Exp. Candy " + size
    assert item.raw["amount"] == amount and item.raw["price"] == amount
    assert item.raw["fieldOnly"] is True and FieldExpCandyUse.supports(item.name)
    gained, total, level = CandyProgression.plan(
        SimpleNamespace(level=50, total_exp=125000), {}, key
    )
    assert gained == amount and total == 125000 + amount and level >= 50


def test_same_level_and_partial_cap_are_real_exp_gains():
    """Same-level feeding is useful; a final partial gain consumes only one copy."""
    assert CandyProgression.plan(SimpleNamespace(level=50, total_exp=125000), {}, "expcandyxs") == (
        100,
        125100,
        50,
    )
    assert CandyProgression.plan(SimpleNamespace(level=99, total_exp=999999), {}, "expcandyxl") == (
        1,
        1000000,
        100,
    )


@pytest.mark.parametrize(
    "level,total",
    [
        (True, 1),
        (1, True),
        (0, 0),
        (101, 1000001),
        (5.0, 125),
        (5, 125.0),
        (5, -1),
        (5, 124),
        (99, 1000000),
    ],
)
def test_bad_saved_progression_is_not_silently_repaired(level, total):
    """Type/range/curve contradictions reject before any resource mutation."""
    with pytest.raises(FieldMedicineError):
        CandyProgression.plan(SimpleNamespace(level=level, total_exp=total), {}, "expcandyxs")


@pytest.mark.parametrize("rate", [None, True, 3, "", "erratic", "unknown"])
def test_unknown_explicit_curve_is_rejected_instead_of_defaulted(rate):
    """Only project-implemented curves are accepted; missing-field default is separate."""
    with pytest.raises(FieldMedicineError):
        CandyProgression.plan(
            SimpleNamespace(level=50, total_exp=125000), {"growthRate": rate}, "expcandyxs"
        )


@pytest.mark.parametrize("level,total", [(100, 1000000), (100, 2000000)])
def test_level_one_hundred_never_consumes_an_exp_candy(level, total):
    """An already capped target cannot turn another copy into a false gain."""
    with pytest.raises(FieldMedicineError):
        CandyProgression.plan(SimpleNamespace(level=level, total_exp=total), {}, "expcandyxl")


@pytest.mark.parametrize("name", ["Candy", "Exp. Candy", "XS", "Exp. Candy XXL", "Rare Candy"])
def test_no_candy_prefix_or_rare_candy_route_expansion(name):
    """Keep the new route separate from existing Rare Candy behavior."""
    assert not FieldExpCandyUse.supports(name)

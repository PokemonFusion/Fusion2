"""Check PP stage rounding and the explicit raw legacy compatibility policy."""

import pytest

from pokemon.services.pp_capacity import PPCapacity


@pytest.mark.parametrize("base, stages", [(5, (0, 1, 2, 3)), (7, (0, 1, 2, 4)),
                                         (25, (0, 5, 10, 15)), (35, (0, 7, 14, 21)),
                                         (40, (0, 8, 16, 24))])
def test_three_integer_rounded_stages(base, stages):
    """Round cumulative fifths down without floating point or a fourth Up."""
    policy = PPCapacity(base)
    assert policy.stages == stages
    assert [policy.increased_bonus(bonus) for bonus in stages] == [*stages[1:], None]
    assert [policy.increased_bonus(bonus, maximize=True) for bonus in stages] == [stages[-1]] * 3 + [None]


@pytest.mark.parametrize("base, blocked", [(0, False), (1, False), (4, False), (5, True), (35, True)])
def test_unboostable_policy(base, blocked):
    """No zero-gain, missing-PP or explicitly blocked move can use either item."""
    policy = PPCapacity(base, blocked)
    assert policy.increased_bonus(0) is None
    assert policy.increased_bonus(0, maximize=True) is None


@pytest.mark.parametrize("bonus", [1, 3, 6, 8, 13, 20])
def test_ambiguous_raw_legacy_bonus_can_only_finish_with_max(bonus):
    """Do not infer old use counts or silently multiply ambiguous saved PP."""
    policy = PPCapacity(35)
    assert policy.increased_bonus(bonus) is None
    assert policy.increased_bonus(bonus, maximize=True) == 21


@pytest.mark.parametrize("bonus", [-1, 21, 22, 65535])
def test_maxed_or_invalid_legacy_row_is_untouched(bonus):
    """Out-of-range rows need explicit recovery; already-maxed rows do nothing."""
    assert PPCapacity(35).increased_bonus(bonus) is None
    assert PPCapacity(35).increased_bonus(bonus, maximize=True) is None

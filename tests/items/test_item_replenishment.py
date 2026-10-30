"""Pure authoring and UTC boundaries for explicitly opted-in replenishment."""

from datetime import datetime, timedelta, timezone
from dataclasses import FrozenInstanceError
from unittest.mock import patch

import pytest

from pokemon.services.item_replenishment import (
    ItemReplenishment,
    ReplenishmentError,
    ReplenishmentPolicy,
)


@pytest.mark.parametrize(
    "source,version,offers",
    [
        ("nonplot-item-supply-v1", 2, (("Potion", 300, 20),)),
        ("", 1, (("Potion", 300, 20),)),
        ("Unsafe Source", 1, (("Potion", 300, 20),)),
        ("qa-source", True, (("Potion", 300, 20),)),
        ("qa-source", 0, (("Potion", 300, 20),)),
        ("qa-source", "1", (("Potion", 300, 20),)),
        ("qa-source", 1, []),
        ("qa-source", 1, ()),
        ("qa-source", 1, (("Potion", 300, None),)),
        ("qa-source", 1, (("Potion", 300, True),)),
        ("qa-source", 1, (("Potion", 300, 0),)),
        ("qa-source", 1, (("Potion", 300, -1),)),
        ("qa-source", 1, (("Potion", True, 20),)),
        ("qa-source", 1, (("Potion", 0, 20),)),
        ("qa-source", 1, (("potion", 300, 20),)),
        ("qa-source", 1, (("Potion", 300, 20), ("Potion", 300, 20))),
        ("qa-source", 1, (("Bicycle", 300, 20),)),
        ("qa-source", 1, (("Master Ball", 300, 20),)),
        ("qa-source", 1, (("Leftovers", 300, 20),)),
        ("qa-source", 1, (("Potion", 300),)),
    ],
)
def test_policy_refuses_ambiguous_unbounded_or_out_of_scope_offers(source, version, offers):
    """Authoring cannot silently turn malformed or plot stock into renewable supply."""
    with pytest.raises(ReplenishmentError):
        ReplenishmentPolicy(source, version, offers)


def test_policy_is_immutable_and_hashes_exact_revision_vector():
    """Reordering is harmless, but price/cap/version/source drift changes identity."""
    policy = ReplenishmentPolicy("qa-source", 1, (("Potion", 300, 20), ("Oran Berry", 80, 20)))
    reverse = ReplenishmentPolicy("qa-source", 1, tuple(reversed(policy.offers)))
    assert ItemReplenishment.digest(policy.identity()) == ItemReplenishment.digest(
        reverse.identity()
    )
    for changed in (
        ReplenishmentPolicy("qa-other", 1, policy.offers),
        ReplenishmentPolicy("qa-source", 2, policy.offers),
        ReplenishmentPolicy("qa-source", 1, (("Potion", 300, 21),)),
        ReplenishmentPolicy("qa-source", 1, (("Potion", 301, 20),)),
    ):
        assert ItemReplenishment.digest(policy.identity()) != ItemReplenishment.digest(
            changed.identity()
        )
    with pytest.raises(FrozenInstanceError):
        policy.version = 2
    mutable = policy.vector()
    mutable["Potion"]["quantity"] = 999
    assert policy.vector()["Potion"]["quantity"] == 20


@pytest.mark.parametrize(
    "value",
    [None, True, "2026-10-25", "2026-10-25T00:00:00", "2026-10-25T00:00:00+01:00", "garbage"],
)
def test_timestamp_requires_canonical_utc(value):
    """Local/midnight date boundaries cannot replace real UTC elapsed time."""
    with pytest.raises(ReplenishmentError):
        ItemReplenishment.timestamp(value)


@pytest.mark.parametrize("value", [None, "now", datetime(2026, 10, 25)])
def test_server_clock_requires_aware_utc(value):
    """Bad server time fails closed before any stock write."""
    with patch.object(ItemReplenishment, "clock", return_value=value):
        with pytest.raises(ReplenishmentError):
            ItemReplenishment.now()


def test_rolling_interval_is_exactly_twenty_four_hours():
    """Crossing midnight alone does not open another refill window."""
    before = datetime(2026, 10, 25, 23, 59, tzinfo=timezone.utc)
    assert ItemReplenishment.timestamp(before.isoformat()) == before
    assert before + ItemReplenishment.interval == datetime(
        2026, 10, 26, 23, 59, tzinfo=timezone.utc
    )
    assert ItemReplenishment.interval == timedelta(hours=24)

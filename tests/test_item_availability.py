"""Prevent definition presence and prepared fixtures from overstating availability."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_item_availability import ItemAvailabilityAudit, live_sources


def snapshot(*objects):
    """Supply explicit world data, with no implicit live/database fallback."""
    return {"world_objects": list(objects)}


def shop(quantity=1, enabled=True):
    """Model the actual flag/finite inventory contract."""
    return {"id": 1, "name": "Test Shop", "attributes": {"is_item_shop": enabled,
            "store_inventory": {"Potion": {"price": 300, "quantity": quantity}}}}


def test_unknown_world_is_never_reported_unavailable_or_obtainable():
    """Missing live data is an unknown rather than an assertion about the world."""
    assert live_sources(None, "potion")["status"] == "unverified"


@pytest.mark.parametrize("quantity,enabled", [(0, True), (5, False), (-1, True), (True, True)])
def test_disabled_empty_or_invalid_shop_does_not_prove_acquisition(quantity, enabled):
    """A room or arbitrary dictionary entry is not usable positive stock."""
    assert not live_sources(snapshot(shop(quantity, enabled)), "potion")["sources"]


def test_positive_stock_retains_price_quantity_and_walkthrough_limit():
    """Configuration proves only a configured source; it is not a player login."""
    row = live_sources(snapshot(shop(3)), "potion")
    assert row["status"] == "configured_unverified_walkthrough"
    assert row["sources"][0]["price"] == 300
    assert row["sources"][0]["quantity"] == 3
    assert "reachability" in row["limit"]


@pytest.mark.parametrize("stock,available", [(None, True), (5, True), (4, False), (0, False), (True, False)])
def test_vendor_must_have_a_full_bundle(stock, available):
    """A finite vendor with fewer than one bundle cannot vend an item."""
    vendor = {"id": 2, "name": "Candy", "location": 3, "attributes": {
        "dispense_item": "Rare Candy", "dispense_quantity": 5, "stock": stock}}
    assert bool(live_sources(snapshot(vendor), "rarecandy")["sources"]) is available


def test_index_separates_supported_effects_from_uninspected_stock_and_deferred_systems():
    """Real catalog scopes preserve command, deferred, source and historical limits."""
    result = ItemAvailabilityAudit().build()
    rows = {row["key"]: row for row in result["items"]}
    assert len(rows) == result["scoped_count"]
    assert "pokeball" not in rows and not any(key.startswith("tr0") for key in rows)
    assert "potion" in rows and "leaderscrest" in rows and "goldbottlecap" in rows
    assert rows["potion"]["world_availability"]["status"] == "unverified"
    assert rows["potion"]["authored_acquisition"][0]["kind"] == "adventure_first_clear"
    assert not rows["freshwater"]["authored_acquisition"]
    assert rows["rarecandy"]["authored_acquisition"][0]["kind"] == "alpha_recipe_vendor"
    assert rows["charizarditex"]["support_status"] == "deferred"
    assert rows["charizarditex"]["followups"] == [774]
    assert 773 in rows["oranberry"]["followups"]
    assert result["historical_matrix"]["status"] == "historical_observations_not_a_fresh_replay"
    assert all(len(row["definition_sha256"]) == 64 for row in rows.values())

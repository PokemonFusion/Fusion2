"""Bind finite source authoring to the exact accepted non-plot contract."""

import pytest

from pokemon.services.finite_item_supply import FINITE_SUPPLY_ROUTES


@pytest.mark.parametrize(
    "issue,count,units,total",
    [
        (877, 6, 80, 19500),
        (878, 4, 42, 52000),
        (879, 4, 22, 51000),
        (880, 6, 30, 90000),
        (881, 6, 12, 120000),
        (882, 4, 5, 84600),
        (883, 6, 20, 30000),
    ],
)
def test_finite_contract_vectors_and_existing_definitions(issue, count, units, total):
    """Prices/aggregate caps are deliberate authored economy values, never defaults."""
    route = FINITE_SUPPLY_ROUTES[issue]
    data = route.recipe()
    assert len(data["offers"]) == count
    assert sum(row["quantity"] for row in data["offers"]) == units
    assert sum(row["quantity"] * row["price"] for row in data["offers"]) == total
    assert {row["item"] for row in data["offers"]} == route.names
    assert data["version"] == 1 and data["refill"] == "none" and data["buy_only"] is True
    assert data["return_exit"] == "back"
    assert "+store" in route.description(data) and "no refill or resale" in route.description(data)
    assert "item_replenishment" not in data


def test_seven_routes_have_distinct_identities_and_no_original_counter_overlap():
    """Retries and source receipts cannot collide across unrelated finite batches."""
    from pokemon.services.item_supply import ItemSupplyRoute

    for field in ("key", "marker", "entrance", "room_name"):
        values = {getattr(route, field) for route in FINITE_SUPPLY_ROUTES.values()}
        assert len(values) == 7
    assert all(
        route.key != ItemSupplyRoute.key and route.marker != ItemSupplyRoute.marker
        for route in FINITE_SUPPLY_ROUTES.values()
    )
    names = {name for route in FINITE_SUPPLY_ROUTES.values() for name in route.names}
    assert len(names) == 36
    assert not names.intersection(
        {"Potion", "Fire Stone", "Bicycle", "Master Ball", "Leader's Crest"}
    )


def test_source_index_records_recipes_without_claiming_installed_stock():
    """New authored counters remain separate from unknown current-world access."""
    from tools.audit_item_availability import ItemAvailabilityAudit
    from pokemon.names import normalize_name

    index = ItemAvailabilityAudit().build()
    rows = {row["key"]: row for row in index["items"]}
    for route in FINITE_SUPPLY_ROUTES.values():
        for name, price, cap in route.offers:
            row = rows[normalize_name(name)]
            source = next(
                source
                for source in row["authored_acquisition"]
                if source["name"] == route.room_name
            )
            assert source["source"] == "pokemon/services/finite_item_supply.py"
            assert source["price"] == price and source["initial_stock"] == cap
            assert source["refill"] == "none"
            assert row["world_availability"]["status"] == "unverified"
            assert not row["world_availability"]["sources"]

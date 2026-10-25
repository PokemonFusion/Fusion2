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
    assert any(source["kind"] == "adventure_first_clear" for source in rows["potion"]["authored_acquisition"])
    assert any(source["kind"] == "opt_in_recipe_shop" for source in rows["freshwater"]["authored_acquisition"])
    assert rows["rarecandy"]["authored_acquisition"][0]["kind"] == "alpha_recipe_vendor"
    assert rows["charizarditex"]["support_status"] == "capability_with_bounded_evidence"
    assert rows["charizarditex"]["followups"] == []
    assert any(route["kind"] == "mega" and route["native"] == "Charizard"
               for route in rows["charizarditex"]["routes"])
    assert 773 not in rows["oranberry"]["followups"]
    assert any(route["command"] == "+item" for route in rows["oranberry"]["routes"])
    assert any(route["kind"] == "food" for route in rows["freshwater"]["routes"])
    assert not any(route["kind"] == "medicine" for route in rows["freshwater"]["routes"])
    for key in ("pomegberry", "figyberry", "sacredash"):
        assert 773 not in rows[key]["followups"]
        assert not any(route["command"] == "+item" for route in rows[key]["routes"])
        assert any("Intentionally excluded" in limit for limit in rows[key]["limits"])
    assert result["historical_matrix"]["status"] == "historical_observations_not_a_fresh_replay"
    assert all(len(row["definition_sha256"]) == 64 for row in rows.values())


def test_new_recovery_and_coin_routes_remain_separate_from_world_availability():
    """Current effects and documented recipes never become a live availability claim."""
    rows = {row["key"]: row for row in ItemAvailabilityAudit().build()["items"]}
    for key in ("ragecandybar", "hopoberry"):
        assert any(route["command"] == "+use" for route in rows[key]["routes"])
        assert not any(route["command"] == "+item" for route in rows[key]["routes"])
        assert rows[key]["world_availability"]["status"] == "unverified"
    assert any("999" in route["limit"] for route in rows["gimmighoulcoin"]["routes"] if route["kind"] == "evolution")
    for key in ("potion", "oranberry", "freshwater", "firestone", "leftovers", "smokeball"):
        assert any(source["kind"] == "opt_in_recipe_shop" for source in rows[key]["authored_acquisition"])
        assert not rows[key]["world_availability"]["sources"]


def test_current_allowlists_preserve_bounded_sources_and_cap_ultra_exclusions():
    """Working systems cannot enable catalog-wide moves or fictional holders."""
    from pokemon.battle.z_profiles import ZProfiles
    from audit_item_availability import current_registries

    result = ItemAvailabilityAudit().build()
    rows = {row["key"]: row for row in result["items"]}
    mega, profiles = current_registries()
    assert result["current_registries"]["mega_pairs"] == len(mega) == 47
    assert result["current_registries"]["z_mappings"] == len(profiles)
    assert result["current_registries"]["z_crystals"] == 34
    assert result["current_registries"]["z_kinds"]["signature"] == 16
    assert {row["key"] for row in result["items"] if any(r["kind"] == "mega" for r in row["routes"])} == set(mega)
    assert "crucibellite" not in rows and "vilevial" not in rows
    assert result["excluded_cap"] == ["Crucibellite", "Vile Vial"]
    assert rows["ultranecroziumz"]["support_status"] == "deferred"
    assert rows["ultranecroziumz"]["followups"] == [865]
    firium = next(route for route in rows["firiumz"]["routes"] if route["kind"] == "z_move")
    assert any(p["source"] == "Ember" and p["power"] == 100 for p in firium["profiles"])
    assert not any(p["source"] == "Fire Blast" for p in firium["profiles"])
    assert ZProfiles.get("Firium Z", "Fire Blast") is None
    assert 864 in rows["firiumz"]["followups"]


def test_snack_growing_and_native_combination_do_not_invent_world_access():
    """Each later route carries its distinct command and acceptance boundary."""
    result = ItemAvailabilityAudit().build()
    rows = {row["key"]: row for row in result["items"]}
    snack = next(r for r in rows["razzberry"]["routes"] if r["kind"] == "berry_snack")
    assert snack["command"].startswith("+berry snack")
    assert not any(r["command"] == "+use" for r in rows["razzberry"]["routes"])
    assert any(r["kind"] == "berry_growing" for r in rows["oranberry"]["routes"])
    assert not any(r["kind"] == "berry_growing" for r in rows["razzberry"]["routes"])
    assert any(s["source"] == "world/berry_nursery.json" for s in rows["razzberry"]["authored_acquisition"])
    for key in ("solganiumz", "lunaliumz"):
        route = next(r for r in rows[key]["routes"] if r["kind"] == "native_necrozma_signature")
        assert route["released_local_report"] == "necrozma-released-retry-2026-10-24"
        assert "shared deployment" in route["limit"]
        assert rows[key]["world_availability"]["status"] == "unverified"
    assert "Local deliberately released build only" in result["native_necrozma"]["limit"]
    assert len(result["repair_receipts"]) == 6
    assert all(len(value) == 64 for value in result["source_identities_sha256_lf"].values())


def test_depleted_disabled_absent_and_unknown_world_sources_are_distinct():
    """A sold-out observed shop is different from no observed source or no data."""
    assert live_sources(None, "potion")["status"] == "unverified"
    assert live_sources(snapshot(), "potion")["status"] == "no_observed_shop_or_vendor_source"
    assert live_sources(snapshot(shop(0)), "potion")["status"] == "observed_depleted_source"
    assert live_sources(snapshot(shop(5, False)), "potion")["status"] == "observed_disabled_or_invalid_source"


def test_six_repair_receipts_keep_exact_named_facets_and_local_limits():
    """A repaired facet cannot certify unrelated items or deployed acquisition."""
    result = ItemAvailabilityAudit().build()
    receipts = {row["issue"]: row for row in result["repair_receipts"]}
    assert {issue: len(row["items"]) for issue, row in receipts.items()} == {
        853: 9, 854: 7, 855: 17, 856: 21, 857: 7, 858: 3}
    rows = {row["key"]: row for row in result["items"]}
    assert {row["issue"] for row in rows["adamantcrystal"]["current_repair_evidence"]} == {854, 857}
    assert {row["issue"] for row in rows["pechaberry"]["current_repair_evidence"]} == {858}
    assert not rows["potion"]["current_repair_evidence"]
    assert all("no fresh live replay" in row["limit"] for row in receipts.values())
    assert all(len(row["sha256_lf"]) == 64 for row in receipts.values())

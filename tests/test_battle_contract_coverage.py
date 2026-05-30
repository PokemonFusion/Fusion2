"""Tests for the battle proof coverage inventory."""

from __future__ import annotations

from pokemon import dex
from tests.battle_contract_coverage import (
    CONTRACTS_BY_SUBJECT,
    COVERAGE_STATUSES,
    EXPLICIT_CONTRACT,
    MECHANIC_CONTRACT,
    SMOKE_ONLY,
    SUPPORTED_MECHANICS,
    build_inventory,
)


REQUIRED_MECHANIC_GROUPS = {
    "status_outcome",
    "stat_boost",
    "healing",
    "drain",
    "recoil",
    "ability_immunity",
    "item_residual",
    "weather",
    "terrain",
    "side_condition",
    "volatile",
    "forced_switch",
    "self_switch",
    "priority",
    "random_branch",
    "damage",
    "secondary_effect",
    "callback_damage",
    "combo_move",
}


def test_semantic_contracts_cover_required_mechanic_groups():
    assert REQUIRED_MECHANIC_GROUPS <= SUPPORTED_MECHANICS


def test_battle_contract_inventory_classifies_every_dex_entry():
    records = build_inventory()
    expected = (
        len(dex.MOVEDEX)
        + len(dex.ABILITYDEX)
        + len(dex.ITEMDEX)
        + len(dex.POKEDEX)
    )

    assert len(records) == expected
    assert {record.status for record in records} <= set(COVERAGE_STATUSES)
    assert all(record.subject for record in records)


def test_contract_subjects_exist_in_loaded_dex_inventory():
    subjects = {record.subject for record in build_inventory()}

    assert set(CONTRACTS_BY_SUBJECT) <= subjects


def test_inventory_uses_explicit_and_mechanic_buckets_without_smoke_only():
    records = build_inventory()
    statuses = {record.status for record in records}

    assert EXPLICIT_CONTRACT in statuses
    assert MECHANIC_CONTRACT in statuses
    assert all(record.status != SMOKE_ONLY for record in records)

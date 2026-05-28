"""Semantic proof contracts for representative battle mechanics."""

from __future__ import annotations

import pytest

from pokemon.battle.tests.outcome_harness import (
    assert_ability_start_outcome,
    assert_ability_event_outcome,
    assert_ability_flag_outcome,
    assert_before_move_outcome,
    assert_form_change_outcome,
    assert_item_event_outcome,
    assert_item_callback_outcome,
    assert_move_event_outcome,
    assert_move_outcome,
    assert_post_battle_ability_outcome,
    assert_residual_outcome,
    assert_run_outcome,
    assert_species_outcome,
    assert_switch_outcome,
)
from tests.battle_contract_catalog import (
    ABILITY_EVENT_CONTRACTS,
    ABILITY_FLAG_CONTRACTS,
    ABILITY_START_CONTRACTS,
    BEFORE_MOVE_CONTRACTS,
    FORM_CHANGE_CONTRACTS,
    ITEM_EVENT_CONTRACTS,
    ITEM_CALLBACK_CONTRACTS,
    MOVE_EVENT_CONTRACTS,
    MOVE_CONTRACTS,
    POST_BATTLE_ABILITY_CONTRACTS,
    RESIDUAL_CONTRACTS,
    RUN_CONTRACTS,
    SPECIES_CONTRACTS,
    SWITCH_CONTRACTS,
)


@pytest.mark.parametrize("contract", MOVE_CONTRACTS, ids=str)
def test_move_and_ability_semantic_contracts(contract):
    assert_move_outcome(contract)


@pytest.mark.parametrize("contract", MOVE_EVENT_CONTRACTS, ids=str)
def test_move_event_semantic_contracts(contract):
    assert_move_event_outcome(contract)


@pytest.mark.parametrize("contract", RESIDUAL_CONTRACTS, ids=str)
def test_item_residual_semantic_contracts(contract):
    assert_residual_outcome(contract)


@pytest.mark.parametrize("contract", ABILITY_START_CONTRACTS, ids=str)
def test_ability_start_semantic_contracts(contract):
    assert_ability_start_outcome(contract)


@pytest.mark.parametrize("contract", ABILITY_FLAG_CONTRACTS, ids=str)
def test_ability_flag_semantic_contracts(contract):
    assert_ability_flag_outcome(contract)


@pytest.mark.parametrize("contract", POST_BATTLE_ABILITY_CONTRACTS, ids=str)
def test_post_battle_ability_semantic_contracts(contract):
    assert_post_battle_ability_outcome(contract)


@pytest.mark.parametrize("contract", RUN_CONTRACTS, ids=str)
def test_run_semantic_contracts(contract):
    assert_run_outcome(contract)


@pytest.mark.parametrize("contract", BEFORE_MOVE_CONTRACTS, ids=str)
def test_before_move_semantic_contracts(contract):
    assert_before_move_outcome(contract)


@pytest.mark.parametrize("contract", SWITCH_CONTRACTS, ids=str)
def test_switch_semantic_contracts(contract):
    assert_switch_outcome(contract)


@pytest.mark.parametrize("contract", ITEM_EVENT_CONTRACTS, ids=str)
def test_item_event_semantic_contracts(contract):
    assert_item_event_outcome(contract)


@pytest.mark.parametrize("contract", ITEM_CALLBACK_CONTRACTS, ids=str)
def test_item_callback_semantic_contracts(contract):
    assert_item_callback_outcome(contract)


@pytest.mark.parametrize("contract", ABILITY_EVENT_CONTRACTS, ids=str)
def test_ability_event_semantic_contracts(contract):
    assert_ability_event_outcome(contract)


@pytest.mark.parametrize("contract", SPECIES_CONTRACTS, ids=str)
def test_species_semantic_contracts(contract):
    assert_species_outcome(contract)


@pytest.mark.parametrize("contract", FORM_CHANGE_CONTRACTS, ids=str)
def test_form_change_semantic_contracts(contract):
    assert_form_change_outcome(contract)

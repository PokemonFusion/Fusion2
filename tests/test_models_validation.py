"""Tests for model validation helpers."""

import sys
import types

import pytest
from django.core.exceptions import ValidationError

from pokemon.models.validators import validate_ivs, validate_evs


@pytest.fixture(autouse=True)
def stub_stats(monkeypatch):
    """Provide a minimal ``pokemon.stats`` module for validator tests."""
    stats_mod = types.ModuleType("pokemon.stats")
    stats_mod.EV_LIMIT = 510
    stats_mod.STAT_EV_LIMIT = 252
    monkeypatch.setitem(sys.modules, "pokemon.stats", stats_mod)


def test_invalid_iv_length():
    with pytest.raises(ValidationError):
        validate_ivs([0, 0, 0, 0, 0])


def test_invalid_iv_value():
    with pytest.raises(ValidationError):
        validate_ivs([0, 0, 0, 0, 0, 32])


def test_invalid_ev_length():
    with pytest.raises(ValidationError):
        validate_evs([0, 0, 0, 0, 0])


def test_invalid_ev_value():
    with pytest.raises(ValidationError):
        validate_evs([0, 0, 253, 0, 0, 0])


def test_invalid_ev_total():
    with pytest.raises(ValidationError):
        validate_evs([252, 252, 5, 1, 0, 1])


def test_valid_values_pass():
    validate_ivs([31] * 6)
    validate_evs([0] * 6)


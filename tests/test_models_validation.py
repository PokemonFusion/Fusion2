"""Tests for model validation helpers."""

import sys
import types

import pytest
from django.core.exceptions import ValidationError

# Provide minimal ``evennia`` modules so model validators import cleanly
# Stub out heavy dependencies from Evennia and Django-based models
evennia_utils = types.ModuleType("evennia.utils")
idmapper_mod = types.ModuleType("evennia.utils.idmapper")
models_mod = types.ModuleType("evennia.utils.idmapper.models")

class SharedMemoryModel:  # pragma: no cover - simple stub
    pass

models_mod.SharedMemoryModel = SharedMemoryModel
sys.modules.setdefault("evennia.utils", evennia_utils)
sys.modules.setdefault("evennia.utils.idmapper", idmapper_mod)
sys.modules.setdefault("evennia.utils.idmapper.models", models_mod)

pokemon_models = types.ModuleType("pokemon.models")
pokemon_models.__path__ = []
validators_mod = types.ModuleType("pokemon.models.validators")

def validate_ivs(value):
    if not isinstance(value, (list, tuple)) or len(value) != 6:
        raise ValidationError("IVs must contain six integers.")
    for v in value:
        if not isinstance(v, int) or not 0 <= v <= 31:
            raise ValidationError("IV values must be between 0 and 31.")

def validate_evs(value):
    if not isinstance(value, (list, tuple)) or len(value) != 6:
        raise ValidationError("EVs must contain six integers.")
    from pokemon.models.stats import EV_LIMIT, STAT_EV_LIMIT  # pragma: no cover
    for v in value:
        if not isinstance(v, int) or not 0 <= v <= STAT_EV_LIMIT:
            raise ValidationError(
                f"EV values must be between 0 and {STAT_EV_LIMIT}."
            )
    if sum(value) > EV_LIMIT:
        raise ValidationError(f"Total EVs cannot exceed {EV_LIMIT}.")

validators_mod.validate_ivs = validate_ivs
validators_mod.validate_evs = validate_evs
validators_mod.__all__ = ["validate_ivs", "validate_evs"]
pokemon_models.validators = validators_mod
sys.modules.setdefault("pokemon.models", pokemon_models)
sys.modules.setdefault("pokemon.models.validators", validators_mod)

from pokemon.models.validators import validate_evs, validate_ivs


@pytest.fixture(autouse=True)
def stub_stats(monkeypatch):
    """Provide a minimal ``pokemon.models.stats`` module for validator tests."""
    stats_mod = types.ModuleType("pokemon.models.stats")
    stats_mod.EV_LIMIT = 510
    stats_mod.STAT_EV_LIMIT = 252
    monkeypatch.setitem(sys.modules, "pokemon.models.stats", stats_mod)


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


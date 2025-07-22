import os
import sys
import ast
import textwrap
import importlib.util
import pytest
from django.core.exceptions import ValidationError

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
models_path = os.path.join(ROOT, "pokemon", "models.py")

source = open(models_path).read()
module = ast.parse(source)
ns = {"ValidationError": ValidationError}
for node in module.body:
    if isinstance(node, ast.ImportFrom) and node.module == 'stats' and node.level == 1:
        exec('from pokemon.stats import EV_LIMIT, STAT_EV_LIMIT', ns)
    if isinstance(node, ast.FunctionDef) and node.name in ("validate_ivs", "validate_evs"):
        code = ast.get_source_segment(source, node)
        exec(textwrap.dedent(code), ns)

validate_ivs = ns['validate_ivs']
validate_evs = ns['validate_evs']


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

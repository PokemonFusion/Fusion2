"""Run item-audit battle findings outside legacy test module stubs."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("name", ["damp_player_cases", "egg_roster_cases"])
def test_battle_player_repairs_database(name):
    """Require explicit isolated PostgreSQL; never fall back to the game database."""
    if not os.environ.get("PF2_TEST_POSTGRES_DSN"):
        pytest.skip("Battle player-flow persistence needs an explicit disposable PostgreSQL DSN.")
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-B", str(root / "tests/integration" / (name + ".py"))],
        cwd=root, env=os.environ.copy(), capture_output=True, text=True, encoding="utf-8", timeout=240,
    )
    assert result.returncode == 0, result.stdout + result.stderr

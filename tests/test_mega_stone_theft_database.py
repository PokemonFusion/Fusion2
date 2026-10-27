"""Keep native Mega Stone command/model proof outside legacy import stubs."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


def test_mega_stone_theft_player_database():
    """Require the explicit disposable-schema DSN, never game database settings."""
    if not os.environ.get("PF2_TEST_POSTGRES_DSN"):
        pytest.skip("Mega Stone player-flow persistence needs an explicit disposable PostgreSQL DSN.")
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-B", str(root / "tests/integration/mega_stone_theft_cases.py")],
        cwd=root, env=os.environ.copy(), capture_output=True, text=True, encoding="utf-8", timeout=300,
    )
    assert result.returncode == 0, result.stdout + result.stderr

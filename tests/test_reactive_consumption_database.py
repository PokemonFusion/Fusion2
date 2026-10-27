"""Qualify reactive item commands separately from legacy battle import adapters."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


def test_reactive_consumption_player_database():
    """Require an explicit disposable DSN, never the configured game database."""
    if not os.environ.get("PF2_TEST_POSTGRES_DSN"):
        pytest.skip("Reactive consumption player flows require explicit disposable PostgreSQL.")
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-B", str(root / "tests/integration/reactive_consumption_cases.py")],
        cwd=root, env=os.environ.copy(), capture_output=True, text=True, encoding="utf-8", timeout=300,
    )
    assert result.returncode == 0, result.stdout + result.stderr

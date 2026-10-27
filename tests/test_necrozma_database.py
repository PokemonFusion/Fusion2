"""Run native-pair SQL coverage separately from the legacy suite's model stubs."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("suite", ("necrozma", "necrozma_lifecycle", "necrozma_player"))
def test_native_necrozma_database(suite):
    """Require an explicit isolated DSN for real custody, rollback and PP checks."""
    if not os.environ.get("PF2_TEST_POSTGRES_DSN"):
        pytest.skip("Native-pair integrity requires an explicit isolated PostgreSQL DSN.")
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, "-B", str(root / f"tests/integration/{suite}_cases.py")],
        cwd=root, env=os.environ.copy(), capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr

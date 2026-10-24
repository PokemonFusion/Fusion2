"""Run actual persistent setup acceptance outside legacy suite model stubs."""
import os
from pathlib import Path
import subprocess
import sys
import pytest


def test_persistent_human_and_fusion_onboarding():
    """Verify real callbacks, receipts, reservations, retries and current ownership."""
    if not os.environ.get("PF2_TEST_POSTGRES_DSN"):
        pytest.skip("Persistent onboarding requires an explicit isolated PostgreSQL DSN.")
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, "-B", "tests/integration/onboarding_cases.py"],
        cwd=root, env=os.environ.copy(), capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr

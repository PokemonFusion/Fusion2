"""Run real communication acceptance outside legacy global model stubs."""
import os
from pathlib import Path
import subprocess
import sys
import pytest


def test_persistent_character_communication():
    """Exercise real Msg/tags, board Attributes, permissions and subscriptions."""
    if not os.environ.get("PF2_TEST_POSTGRES_DSN"):
        pytest.skip("Persistent communications require an explicit isolated PostgreSQL DSN.")
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, "-B", "tests/integration/communication_cases.py"],
        cwd=root, env=os.environ.copy(), capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr

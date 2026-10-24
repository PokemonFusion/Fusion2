"""Run actual four-account Multi input outside legacy global engine stubs."""
import os
from pathlib import Path
import subprocess
import sys
import pytest


def test_persistent_four_controller_multi_battles():
    """Exercise real lobbies, ordinary commands, team effects and durable cleanup."""
    if not os.environ.get('PF2_TEST_POSTGRES_DSN'):
        pytest.skip('Multi Battle persistence needs the explicit isolated PostgreSQL DSN.')
    result = subprocess.run([sys.executable, '-B', 'tests/integration/multi_battle_cases.py'],
        cwd=Path(__file__).resolve().parents[1], env=os.environ.copy(), capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, result.stdout + result.stderr

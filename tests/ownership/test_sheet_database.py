"""Keep actual profile and sheet requests separate from global stub collection."""
import os
from pathlib import Path
import subprocess
import sys
import pytest


def test_persistent_character_sheets():
    """Verify canonical ownership, private fields and request permissions."""
    if not os.environ.get('PF2_TEST_POSTGRES_DSN'):
        pytest.skip('Character sheets require the explicit isolated PostgreSQL DSN.')
    result = subprocess.run([sys.executable, '-B', 'tests/integration/sheet_cases.py'],
        cwd=Path(__file__).resolve().parents[2], env=os.environ.copy(), capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr

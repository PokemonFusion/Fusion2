"""Exercise production Adventure persistence with real SQLite transactions."""

import subprocess
import sys
from pathlib import Path


def test_adventure_recovery_transactions():
    """Keep Django's real registry separate from legacy import-time test stubs."""

    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, str(root / "tests" / "helpers" / "adventure_recovery_orm.py")],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Adventure recovery ORM checks passed" in result.stdout

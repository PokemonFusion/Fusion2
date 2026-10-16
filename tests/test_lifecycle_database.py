"""Run real ORM lifecycle coverage outside the legacy suite's global model stubs."""

import os
import subprocess
import sys
from pathlib import Path


def test_canonical_lifecycle_database():
    """Exercise real transactions; PostgreSQL-only cases require an explicit DSN."""
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "tests/integration/placement_cases.py")],
        cwd=root, env=os.environ.copy(), capture_output=True, text=True, timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_merged_migration_graph():
    """Keep independently merged features on one deployable migration graph."""
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "tests/integration/migration_graph.py")],
        cwd=root, env=os.environ.copy(), capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr

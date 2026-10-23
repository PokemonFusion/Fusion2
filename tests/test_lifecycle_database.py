"""Run real ORM lifecycle coverage outside the legacy suite's global model stubs."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


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


def test_cross_owner_database():
    """Run real PostgreSQL consent, reservation, receipt and contention coverage."""
    if not os.environ.get("PF2_TEST_POSTGRES_DSN"):
        pytest.skip("Cross-owner locking requires an explicit isolated PostgreSQL DSN.")
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-B", str(root / "tests/integration/ownership_cases.py")],
        cwd=root, env=os.environ.copy(), capture_output=True, text=True, timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_fusion_transition_database():
    """Exercise actual Fusion commands and failures outside global model stubs."""
    if not os.environ.get("PF2_TEST_POSTGRES_DSN"):
        pytest.skip("Fusion transaction/concurrency coverage requires an explicit isolated PostgreSQL DSN.")
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-B", str(root / "tests/integration/fusion_cases.py")],
        cwd=root, env=os.environ.copy(), capture_output=True, text=True, timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr

"""Verify gym badge recovery using real, isolated database transactions."""

import subprocess
import sys
from pathlib import Path


def test_gym_rewards_transactions_and_migration_state():
    """Run production models away from legacy stubs and the game database."""
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, str(root / "tests" / "helpers" / "gym_rewards_orm.py")],
        cwd=root, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Gym recovery ORM checks passed" in result.stdout

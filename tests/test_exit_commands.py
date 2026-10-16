"""Run real Evennia exit coverage separately from legacy import-time stubs."""

import subprocess
import sys
from pathlib import Path


def test_exit_aliases_survive_core_command_collisions():
    """Verify parsing, command precedence, ambiguity and traversal locks."""
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "tests/helpers/exit_commands_evennia.py")],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Real Evennia exit command checks passed" in result.stdout

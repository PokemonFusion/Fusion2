"""Exercise real AMP responders outside the legacy suite's Evennia stubs."""

import os
import subprocess
import sys
from pathlib import Path


def test_real_amp_reload_routing():
    """Validate launcher separation, queued input and session resynchronization."""
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, str(root / "tests/integration/amp_reload_cases.py")],
        cwd=root, env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr

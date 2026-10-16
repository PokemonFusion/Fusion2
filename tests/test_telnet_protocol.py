"""Run real protocol checks outside the legacy suite's Evennia import stubs."""

import os
import subprocess
import sys
from pathlib import Path


def test_real_telnet_byte_stream_regressions():
    """Validate packet framing and the configured protocol using real dependencies."""
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "tests/integration/telnet_protocol_cases.py")],
        cwd=root, env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr

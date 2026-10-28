"""Keep real Twisted lifecycle tests outside the suite's legacy Evennia stubs."""

import os
from pathlib import Path
import subprocess
import sys
import pytest


@pytest.mark.parametrize('script', ['server_shutdown_cases.py', 'reload_socket_cases.py'])
def test_reload_listener_shutdown_order(script):
    """Reproduce a real port collision and check the project shutdown barrier."""
    root = Path(__file__).resolve().parents[1]
    execution = subprocess.run(
        [sys.executable, '-B', str(root / 'tests/integration' / script)],
        cwd=root, env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
        capture_output=True, text=True, encoding='utf-8', timeout=45,
    )
    assert execution.returncode == 0, execution.stdout + execution.stderr

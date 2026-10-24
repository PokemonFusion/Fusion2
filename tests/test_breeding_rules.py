"""Verify real breeding dex rules outside legacy modules' global fake catalogs."""

import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


def test_breeding_rules_against_real_dex():
    """Run actual species/move data checks in a fresh isolated Python process."""
    root = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    environment.update(PF2_NO_EVENNIA="1", PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(root))
    environment.pop("PYTEST_ADDOPTS", None)
    with TemporaryDirectory(prefix=".pytest-basetemp-breeding-rules-", dir=root) as temporary:
        result = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q",
            "tests/integration/breeding_rule_cases.py", "-o", "addopts=", "--basetemp", temporary,
            "-o", "cache_dir=" + str(Path(temporary) / "cache")],
            cwd=root, env=environment, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr

"""Keep real ANSI rendering checks separate from legacy module stubs."""

import subprocess
import sys
from pathlib import Path


def test_real_hp_bars_and_battle_hud_have_no_stray_reset_text():
    """The transmitted Telnet and HTML text must retain bars without literal n."""
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, str(root / "tests/helpers/battle_hp_render.py")],
        cwd=root, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Real HP render checks passed" in result.stdout

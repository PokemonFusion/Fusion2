"""Keep real Evennia parsing checks isolated from legacy import stubs."""

import subprocess
import sys
from pathlib import Path


def test_compact_battle_real_ansi_and_html_rendering():
    """Exercise all compact widths and modes with database connections refused."""
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-B", str(root / "tests/helpers/compact_battle_render.py")],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "15 width/mode cases passed" in result.stdout


def test_compact_battle_production_command_flow():
    """Keep real commands and the engine isolated from legacy module stubs."""
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-B", str(root / "tests/helpers/compact_battle_player_flow.py")],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "production command inputs passed" in result.stdout


def test_matching_names_in_production_commands_and_turn_results():
    """Resolve same-named doubles/Multi targets and render their exact positions."""
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-B", str(root / "tests/helpers/battler_labels_player_flow.py")],
        cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "doubles: matching-name selectors and resolved results passed" in result.stdout
    assert "multi: matching-name selectors and resolved results passed" in result.stdout
    assert "singles: matching-name selectors and resolved results passed" in result.stdout

"""Exercise the production collector against import-time application stubs."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest


@pytest.mark.parametrize("reverse", (False, True), ids=("stub-first", "battle-first"))
def test_import_stubs_do_not_replace_battle_effects(tmp_path, reverse):
    """Keep a stub usable by its owner while real Electric Terrain still works."""
    root = Path(__file__).resolve().parents[1]
    (tmp_path / "conftest.py").write_text((root / "conftest.py").read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (tmp_path / "test_stub.py").write_text(dedent('''\
        import sys
        from types import ModuleType

        import pokemon

        stub = ModuleType("pokemon.battle")
        stub.marker = "legacy stub"
        sys.modules["pokemon.battle"] = stub
        pokemon.battle = stub

        def test_owner_retains_its_imports():
            import pokemon.battle
            assert pokemon.battle is stub
            assert sys.modules["pokemon.battle"] is stub
    '''), encoding="utf-8")
    (tmp_path / "test_terrain.py").write_text(dedent('''\
        import sys

        import pokemon.battle
        from pokemon.battle.tests.outcome_harness import assert_move_outcome
        from tests.battle_contract_catalog import MOVE_CONTRACTS

        def test_real_effect_handlers_share_module_identity():
            assert pokemon.battle is sys.modules["pokemon.battle"]
            assert not hasattr(pokemon.battle, "marker")
            contract = next(contract for contract in MOVE_CONTRACTS
                            if contract.name == "electric terrain starts electric terrain")
            assert_move_outcome(contract)
    '''), encoding="utf-8")
    suites = ["test_stub.py", "test_terrain.py"]
    if reverse:
        suites.reverse()
    environment = os.environ.copy()
    environment.update(PF2_NO_EVENNIA="1", PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(root))
    environment.pop("PYTEST_ADDOPTS", None)
    result = subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "-q", *suites],
        cwd=tmp_path, env=environment, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "2 passed" in result.stdout

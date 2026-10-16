"""Run the mandatory battle gate in fresh processes and both suite orders."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


class MandatoryTestGate:
    """Prove the combined suite passes repeatedly without import-order coupling."""

    runs = (
        ("combined", ("tests", "pokemon/battle/tests")),
        ("repeat", ("tests", "pokemon/battle/tests")),
        ("battle-first", ("pokemon/battle/tests", "tests")),
    )

    def run(self) -> int:
        """Stop at the first failed clean-process run and return its exit code."""
        root = Path(__file__).resolve().parents[1]
        environment = os.environ.copy()
        environment.update(
            PF2_NO_EVENNIA="1",
            PYTHONDONTWRITEBYTECODE="1",
            PYTHONPATH=str(root),
        )
        # Ambient pytest arguments must not silently omit callbacks or split
        # this gate across workers; all suites must coexist in one process.
        environment.pop("PYTEST_ADDOPTS", None)
        with TemporaryDirectory(prefix=".pytest-basetemp-mandatory-", dir=root) as temporary:
            for name, suites in self.runs:
                command = [sys.executable, "-B", "-m", "pytest", "-q", *suites,
                           "--run-callback-tests", "-o", "addopts=",
                           "--basetemp", str(Path(temporary) / name)]
                print(f"Mandatory battle gate: {name}", flush=True)
                result = subprocess.run(command, cwd=root, env=environment)
                if result.returncode:
                    return result.returncode
        return 0


if __name__ == "__main__":
    raise SystemExit(MandatoryTestGate().run())

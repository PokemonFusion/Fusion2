#!/usr/bin/env python3
"""Assess and optionally rewrite the repository's CI workflow.

This helper inspects the existing GitHub Actions workflow and provides
recommendations for speeding up pull request feedback while retaining full
coverage on ``main`` and nightly runs. It can also write a proposed workflow
and ``.coveragerc`` when invoked with ``--write``.

Usage examples::

    python tools/ci_assessor.py
    python tools/ci_assessor.py --write
"""

# Purpose: Inspect current CI workflow and print concrete, repo-aware recommendations.
# Optional: write a proposed faster workflow to .github/workflows/ci.yml (behind --write).
# Notes: Tabs for indentation per project conventions.

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WF = REPO_ROOT / ".github" / "workflows" / "ci.yml"
COVERAGERC = REPO_ROOT / ".coveragerc"
REQ_DEV = REPO_ROOT / "requirements-dev.txt"

PROPOSED_YAML = """\
name: CI
on:
  pull_request:
    branches: [main]
    paths-ignore:
      - 'README.md'
      - 'docs/**'
      - '.github/**'
  push:
    branches: [main]
  schedule:
    - cron: '0 6 * * *'

concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
          cache-dependency-path: |
            requirements.txt
            requirements-dev.txt
      - name: Install dev deps
        run: |
          pip install -U pip
          pip install -r requirements-dev.txt
      - name: Ruff
        run: ruff check .

  test:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    env:
      PF2_NO_EVENNIA: "1"
      PYTHONDONTWRITEBYTECODE: "1"
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
          cache-dependency-path: |
            requirements.txt
            requirements-dev.txt
      - name: Install dev deps
        run: |
          pip install -U pip
          pip install -r requirements-dev.txt
          pip install pytest-xdist
      - name: Run tests (no coverage)
        run: |
          pytest -q -n auto --dist=loadgroup --durations=25

  test-with-coverage:
    runs-on: ubuntu-latest
    if: github.event_name != 'pull_request'
    env:
      PF2_NO_EVENNIA: "1"
      PYTHONDONTWRITEBYTECODE: "1"
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
          cache-dependency-path: |
            requirements.txt
            requirements-dev.txt
      - name: Install deps
        run: |
          pip install -U pip
          pip install -r requirements-dev.txt
          pip install pytest-xdist coverage[toml]
      - name: Run tests with coverage (parallel)
        run: |
          coverage run -m pytest -q -n auto --dist=loadgroup --durations=25
          coverage combine
          coverage xml
      - name: Coverage report
        if: always()
        run: coverage report -m || true
"""

PROPOSED_COVERAGERC = """\
[run]
parallel = True
source =
pokemon
utils
commands
omit =
*/tests/*
*/migrations/*
*/__init__.py

[report]
skip_empty = True
show_missing = True
"""


def load_yaml(p: Path):
	"""Return parsed YAML from *p* or ``None`` on failure."""
	if not p.exists():
		return None
	try:
		return yaml.safe_load(p.read_text())
	except Exception as e:  # pragma: no cover - log-only path
		print(f"[warn] Failed to parse {p}: {e}", file=sys.stderr)
		return None


def has_pip_cache(wf) -> bool:
	"""Check if any job uses the pip cache in ``actions/setup-python``."""
	if not wf:
		return False

	def step_uses_setup(step):
		return isinstance(step, dict) and step.get("uses", "").startswith("actions/setup-python@")

	for job in (wf.get("jobs") or {}).values():
		for step in job.get("steps", []):
			if step_uses_setup(step):
				with_ = step.get("with", {})
				if with_.get("cache") == "pip":
					return True
	return False


def runs_coverage_on_prs(wf) -> bool:
	"""Return ``True`` if any pull-request job executes coverage tools."""
	if not wf:
		return False
	# Heuristic: any pull_request job step invoking "coverage run" or "pytest --cov"
	on = wf.get("on", {})
	prs_enabled = "pull_request" in on
	if not prs_enabled:
		return False
	for name, job in (wf.get("jobs") or {}).items():  # pylint: disable=unused-variable
		cond = job.get("if", "")
		steps = job.get("steps", [])
		if "pull_request" in cond or cond == "":
			for s in steps:
				if isinstance(s, dict):
					cmd = "\n".join([s.get("run", "")])
					if "coverage run" in cmd or "--cov" in cmd:
						return True
	return False


def has_concurrency_cancel(wf) -> bool:
	"""Return ``True`` if workflow enables concurrency cancelation."""
	if not wf:
		return False
	cc = wf.get("concurrency") or {}
	return bool(cc.get("cancel-in-progress"))


def uses_xdist(wf) -> bool:
	"""Return ``True`` if any job invokes pytest with ``-n`` for xdist."""
	if not wf:
		return False
	for job in (wf.get("jobs") or {}).values():
		for step in job.get("steps", []):
			if isinstance(step, dict):
				run = step.get("run", "")
				if "pytest" in run and "-n" in run:
					return True
	return False


def main():
	"""Command-line entry point."""
	parser = argparse.ArgumentParser()
	parser.add_argument("--write", action="store_true", help="Write proposed workflow and .coveragerc")
	parser.add_argument("--markdown", action="store_true", help="Emit assessment in Markdown format")
	args = parser.parse_args()

	wf = load_yaml(WF)
	print(f"[info] Workflow file: {WF if WF.exists() else '(missing)'}")

	issues = []
	if not wf:
		issues.append("- No CI workflow found or failed to parse.")
	else:
		if not has_pip_cache(wf):
			issues.append("- Pip cache not enabled in actions/setup-python (adds ~30-60s per job).")
		if runs_coverage_on_prs(wf):
			issues.append("- Coverage runs on pull_request (move to push/main & nightly to cut PR time).")
		if not has_concurrency_cancel(wf):
			issues.append("- No concurrency cancel; new pushes won't auto-cancel older PR runs.")
		if not uses_xdist(wf):
			issues.append("- Pytest-xdist not used; enable -n auto to parallelize tests.")

	if not COVERAGERC.exists():
		issues.append("- .coveragerc missing; add to limit measured source and speed up coverage.")

	if REQ_DEV.exists():
		dev = REQ_DEV.read_text()
		if "pytest-xdist" not in dev:
			issues.append("- pytest-xdist not in requirements-dev.txt; add for parallel test runs.")
	else:
		issues.append("- requirements-dev.txt missing; create and pin dev tooling.")

	if args.markdown:
		print("# CI Assessment\n")
		print(f"- Workflow file: `{WF if WF.exists() else '(missing)'}`")
		print(f"- Coveragerc: `{COVERAGERC if COVERAGERC.exists() else '(missing)'}`\n")
		if issues:
			print("## Recommended changes\n")
			for it in issues:
				print(f"- [ ] {it}")
			print(
				"\n> Tip: run `python tools/ci_assessor.py --write` "
				"to write a proposed faster workflow and `.coveragerc`."
			)
		else:
			print("✅ CI looks good relative to our targets (fast PR runs, coverage on `main`/nightly).")
	else:
		if issues:
			print("[assessment] Recommended changes:")
			for it in issues:
				print(it)
		else:
			print("[assessment] CI looks good relative to our targets.")

	if args.write:
		WF.parent.mkdir(parents=True, exist_ok=True)
		WF.write_text(PROPOSED_YAML)
		print(f"[write] Wrote proposed workflow to {WF}")
		if not COVERAGERC.exists():
			COVERAGERC.write_text(PROPOSED_COVERAGERC)
			print(f"[write] Created {COVERAGERC}")
		else:
			print(f"[skip] {COVERAGERC} already exists; not overwriting.")


if __name__ == "__main__":
	main()

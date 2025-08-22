#!/usr/bin/env python3
"""
org_score.py - Evaluate repository organization.

Run with:
    python tools/org_score.py

Prints a JSON object with an overall score (0-100), a letter grade and a
category breakdown.
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Iterable

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")

# directories or files to skip while walking the repository
IGNORES = {
	".git",
	".venv",
	"venv",
	"__pycache__",
	".pytest_cache",
	"node_modules",
	".idea",
	".vscode",
}


def walk() -> Iterable[str]:
	"""Yield all file paths within ``ROOT`` excluding ignored directories."""

	for dirpath, dirnames, filenames in os.walk(ROOT):
		parts = set(dirpath.replace(ROOT, "", 1).strip(os.sep).split(os.sep))
		if parts & IGNORES:
			dirnames[:] = [d for d in dirnames if d not in IGNORES]
			continue
		for filename in filenames:
			yield os.path.relpath(os.path.join(dirpath, filename), ROOT)


FILES = list(walk())
NAMES = set(FILES)


def has(path: str) -> bool:
	"""Return ``True`` if ``path`` exists in the walked files."""

	return any(p == path or p.endswith("/" + path) for p in NAMES)


def any_in(prefix: str) -> bool:
	"""Return ``True`` if any path starts with ``prefix/``."""

	return any(p.startswith(prefix + "/") for p in NAMES)


score = 0
detail: dict[str, int] = {}

# Top-level layout (10)
top = 0
top += 2 if has("README.md") else 0
top += 1 if has("LICENSE") or has("LICENSE.md") else 0
top += 1 if has("CONTRIBUTING.md") else 0
top += 2 if any_in("docs") else 0
top += 2 if any_in("tests") else 0
top += 2 if any_in("scripts") or any_in("tools") else 0
detail["top_level_layout"] = top
score += min(top, 10)

# Evennia alignment (15)
even = 0
even += 5 if any_in("commands") else 0
even += 5 if any_in("web") else 0
even += 3 if any_in("typeclasses") else 0
even += 2 if any_in("world") or any_in("server") else 0
detail["evennia_alignment"] = even
score += min(even, 15)

# Domain separation (10)
domain = 0
domain += 3 if any_in("pokemon") else 0
domain += 3 if any_in("utils") else 0
domain += 2 if any_in("data") or "moves" in "".join(FILES).lower() else 0
domain += 2 if any_in("ui") or any_in("menus") else 0
detail["domain_separation"] = domain
score += min(domain, 10)

# Naming & structure (10)
bad_names = [p for p in FILES if re.search(r"[A-Z ]", os.path.basename(p)) and p.endswith(".py")]
name_score = 10
if bad_names:
	name_score -= min(4, len(bad_names))
detail["naming_structure"] = max(0, name_score)
score += max(0, name_score)

# Data hygiene (10)
data = 0
data += 4 if any_in("data") or any("dex" in p.lower() for p in FILES) else 0
data += 3 if has(".gitignore") else 0
data += 3 if not any(p.endswith((".sqlite", ".db")) for p in FILES) else 0
detail["data_hygiene"] = data
score += min(data, 10)

# Tests (10)
tests = 0
tests += 6 if any_in("tests") else 0
tests += 2 if has("pytest.ini") or has("pyproject.toml") else 0
tests += 2 if any("test" in os.path.basename(p).lower() for p in FILES) else 0
detail["tests"] = min(tests, 10)
score += min(tests, 10)

# Dev UX (10)
devux = 0
devux += 3 if has("Makefile") else 0
devux += 3 if has("requirements.txt") or has("pyproject.toml") else 0
devux += 2 if has(".env.example") else 0
devux += 2 if has(".editorconfig") else 0
detail["dev_ux"] = devux
score += min(devux, 10)


def _reads(path: str) -> str:
	"""Return the contents of ``path`` or an empty string if missing."""

	try:
		with open(path, "r", encoding="utf-8", errors="ignore") as handle:
			return handle.read()
	except FileNotFoundError:
		return ""


# Linting & types (10)
lint = 0
pyproj = _reads("pyproject.toml")
lint += 4 if has("ruff.toml") or ("ruff" in pyproj) else 0
lint += 3 if has("mypy.ini") or ("mypy" in pyproj) else 0
lint += 3 if has(".pre-commit-config.yaml") else 0
detail["lint_types"] = lint
score += min(lint, 10)

# Docs (7)
docs = 0
docs += 3 if any_in("docs") else 0
docs += 2 if has("README.md") else 0
docs += 2 if any("adr" in p.lower() for p in FILES) else 0
detail["docs"] = min(docs, 7)
score += min(docs, 7)

# Assets/web (4)
assets = 0
assets += 2 if any_in("web/templates") else 0
assets += 2 if any_in("web/static") else 0
detail["assets_web"] = assets
score += min(assets, 4)

# CI/CD (4)
ci = 0
ci += 4 if any_in(".github/workflows") else 0
detail["ci_cd"] = ci
score += min(ci, 4)

# Grade mapping
grade = "F"
if score >= 90:
	grade = "A"
elif score >= 80:
	grade = "B"
elif score >= 70:
	grade = "C"
elif score >= 60:
	grade = "D"


def main() -> None:
	"""Compute and print the organization score."""

	print(
		json.dumps(
			{
				"root": ROOT,
				"score": score,
				"grade": grade,
				"breakdown": detail,
			},
			indent=2,
		)
	)


if __name__ == "__main__":
	main()

"""Shared pytest options for Fusion2 tests."""

from __future__ import annotations

import pytest


def pytest_addoption(parser):
	group = parser.getgroup("fusion2")
	group.addoption(
		"--run-dex-tests",
		action="store_true",
		default=False,
		help="Run exhaustive move, ability, item, and Pokemon dex tests",
	)
	group.addoption(
		"--run-showdown-tests",
		action="store_true",
		default=False,
		help="Run differential tests against the local Pokemon Showdown checkout",
	)
	group.addoption(
		"--run-callback-tests",
		action="store_true",
		default=False,
		help="Run generated move callback resolution and adapter tests",
	)


def pytest_configure(config):
	config.addinivalue_line("markers", "dex: mark test as part of the exhaustive dex suite")
	config.addinivalue_line(
		"markers",
		"showdown: mark test as requiring the local Pokemon Showdown differential runner",
	)
	config.addinivalue_line(
		"markers",
		"callbacks: mark test as part of the generated move callback suite",
	)


def pytest_collection_modifyitems(config, items):
	skip_dex = pytest.mark.skip(reason="need --run-dex-tests option to run")
	skip_showdown = pytest.mark.skip(reason="need --run-showdown-tests option to run")
	skip_callbacks = pytest.mark.skip(reason="need --run-callback-tests option to run")
	for item in items:
		if "dex" in item.keywords and not config.getoption("--run-dex-tests"):
			item.add_marker(skip_dex)
		if "showdown" in item.keywords and not config.getoption("--run-showdown-tests"):
			item.add_marker(skip_showdown)
		if "callbacks" in item.keywords and not config.getoption("--run-callback-tests"):
			item.add_marker(skip_callbacks)

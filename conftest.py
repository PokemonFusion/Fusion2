"""Shared pytest options and import isolation for all Fusion2 test suites."""

from __future__ import annotations

import sys
import types

import pytest


_ORIGINAL_ENSURE_CONNECTION = None


def _refuse_offline_database_connection(self):
	"""Keep unit/dex tests out of the running game's database, even after setup."""
	raise RuntimeError(
		"Offline pytest cannot access a database. Use a guarded disposable-schema "
		"runner from tests/integration for production-model integration checks."
	)


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
	# PF2_NO_EVENNIA skips application bootstrap, but it does not prevent a
	# late Django setup/import from exposing the real ServerConfig manager.
	# Guard at the connection boundary before test-module collection begins.
	global _ORIGINAL_ENSURE_CONNECTION
	from django.db.backends.base.base import BaseDatabaseWrapper

	if _ORIGINAL_ENSURE_CONNECTION is None:
		_ORIGINAL_ENSURE_CONNECTION = BaseDatabaseWrapper.ensure_connection
	BaseDatabaseWrapper.ensure_connection = _refuse_offline_database_connection
	config.addinivalue_line("markers", "dex: mark test as part of the exhaustive dex suite")
	config.addinivalue_line(
		"markers",
		"showdown: mark test as requiring the local Pokemon Showdown differential runner",
	)
	config.addinivalue_line(
		"markers",
		"callbacks: mark test as part of the generated move callback suite",
	)


def pytest_unconfigure(config):
	"""Restore the library method for callers embedding pytest in a process."""
	global _ORIGINAL_ENSURE_CONNECTION
	if _ORIGINAL_ENSURE_CONNECTION is not None:
		from django.db.backends.base.base import BaseDatabaseWrapper

		BaseDatabaseWrapper.ensure_connection = _ORIGINAL_ENSURE_CONNECTION
		_ORIGINAL_ENSURE_CONNECTION = None


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


_PROTECTED_MODULE_ROOTS = (
	"commands",
	"evennia",
	"fusion2",
	"menus",
	"pokemon",
	"typeclasses",
	"utils",
	"world",
)


def _is_protected_module(name: str) -> bool:
	"""Identify application modules that legacy tests replace with stubs."""
	return any(name == root or name.startswith(f"{root}.") for root in _PROTECTED_MODULE_ROOTS)


def _snapshot_modules():
	"""Capture module identities and globals for one test module's imports."""
	modules = {}
	attrs = {}
	for name, module in list(sys.modules.items()):
		if not _is_protected_module(name):
			continue
		modules[name] = module
		if isinstance(module, types.ModuleType):
			attrs[name] = module.__dict__.copy()
	return modules, attrs


def _restore_modules(snapshot) -> None:
	"""Restore the captured imports, including parent-package attributes."""
	modules, attrs = snapshot
	for name in list(sys.modules):
		if _is_protected_module(name) and name not in modules:
			sys.modules.pop(name, None)
	for name, module in modules.items():
		sys.modules[name] = module
		if isinstance(module, types.ModuleType):
			saved_attrs = attrs.get(name)
			if saved_attrs is not None:
				module.__dict__.clear()
				module.__dict__.update(saved_attrs)


class _IsolatedModule(pytest.Module):
	"""Keep legacy import-time test stubs from leaking into other test modules."""

	def _getobj(self):
		"""Collect this test module without leaking its import-time stubs."""
		self._pre_import_modules = _snapshot_modules()
		try:
			module = super()._getobj()
			self._runtime_modules = _snapshot_modules()
			return module
		finally:
			_restore_modules(self._pre_import_modules)

	def setup(self) -> None:
		"""Activate the same imports the test module saw during collection."""
		runtime_modules = getattr(self, "_runtime_modules", None)
		if runtime_modules is not None:
			_restore_modules(runtime_modules)
		super().setup()

	def teardown(self) -> None:
		"""Release this module's stubs before the next test module runs."""
		pre_import_modules = getattr(self, "_pre_import_modules", None)
		if pre_import_modules is not None:
			_restore_modules(pre_import_modules)
		super().teardown()


def pytest_pycollect_makemodule(module_path, parent):
	"""Apply the shared collector to application and battle-mechanics tests."""
	return _IsolatedModule.from_parent(parent, path=module_path)

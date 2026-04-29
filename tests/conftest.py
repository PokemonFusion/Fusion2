import pytest
import sys
import types


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
	return any(name == root or name.startswith(f"{root}.") for root in _PROTECTED_MODULE_ROOTS)


def _snapshot_modules():
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
		self._pre_import_modules = _snapshot_modules()
		try:
			module = super()._getobj()
			self._runtime_modules = _snapshot_modules()
			return module
		finally:
			_restore_modules(self._pre_import_modules)

	def setup(self) -> None:
		runtime_modules = getattr(self, "_runtime_modules", None)
		if runtime_modules is not None:
			_restore_modules(runtime_modules)
		super().setup()

	def teardown(self) -> None:
		pre_import_modules = getattr(self, "_pre_import_modules", None)
		if pre_import_modules is not None:
			_restore_modules(pre_import_modules)
		super().teardown()


def pytest_pycollect_makemodule(module_path, parent):
	return _IsolatedModule.from_parent(parent, path=module_path)


def pytest_addoption(parser):
	parser.addoption(
		"--run-dex-tests",
		action="store_true",
		default=False,
		help="Run exhaustive move and ability tests",
	)


def pytest_configure(config):
	config.addinivalue_line("markers", "dex: mark test as part of the exhaustive dex suite")


def pytest_collection_modifyitems(config, items):
	if config.getoption("--run-dex-tests"):
		return
	skip_dex = pytest.mark.skip(reason="need --run-dex-tests option to run")
	for item in items:
		if "dex" in item.keywords:
			item.add_marker(skip_dex)

"""Backward compatibility wrapper for move callback implementations."""

try:  # pragma: no cover - exercised in tests with package context
	from .moves import *  # noqa: F401,F403
	from .moves import __all__  # noqa: F401
except Exception:  # pragma: no cover - fallback for ad-hoc loading
	try:
		from pokemon.dex.functions.moves import *  # noqa: F401,F403
		from pokemon.dex.functions.moves import __all__  # noqa: F401
	except Exception:  # pragma: no cover - manual filesystem import
		import importlib.util
		import sys
		from pathlib import Path

		path = Path(__file__).with_name("moves") / "__init__.py"
		spec = importlib.util.spec_from_file_location("pokemon.dex.functions.moves", path)
		module = importlib.util.module_from_spec(spec)
		sys.modules[spec.name] = module
		spec.loader.exec_module(module)
		globals().update({k: getattr(module, k) for k in getattr(module, "__all__", [])})
		__all__ = getattr(module, "__all__", [])

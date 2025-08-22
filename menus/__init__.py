"""Lightweight package for EvMenu flows.

The individual menu modules may depend on optional frameworks such as Evennia
or Django. To avoid import-time errors in environments where these
dependencies are missing (e.g. the test suite), the package does not eagerly
import any submodules. Import the desired menu directly, for example::

    from menus import learn_new_moves

The normal :class:`ImportError` will be raised if a menu module cannot be
loaded.
"""

from importlib import import_module
from types import ModuleType

__all__: list[str] = []


def __getattr__(name: str) -> ModuleType:
    """Dynamically import menu submodules on first access.

    This mirrors ``importlib.import_module("menus.<name>")`` while caching the
    result on the package to avoid repeated imports.
    """

    try:
        module = import_module(f"{__name__}.{name}")
    except ModuleNotFoundError as exc:  # pragma: no cover - propagate standard error
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    globals()[name] = module
    __all__.append(name)
    return module


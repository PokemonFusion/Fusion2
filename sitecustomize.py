"""Site-wide customizations for Fusion2 tests.

This module hooks into Python's import machinery to ensure that any
suppressed import errors are logged.  The log includes the module being
imported, the module performing the import and the original exception
information.  Python automatically imports this module on startup when it
is present on the ``PYTHONPATH``.
"""

from __future__ import annotations

import builtins
import inspect
import logging
from types import ModuleType
from typing import Any

# Preserve the original import function so we can delegate to it.
_original_import = builtins.__import__
logger = logging.getLogger("import_errors")


def _import_with_logging(
    name: str,
    globals: dict[str, Any] | None = None,
    locals: dict[str, Any] | None = None,
    fromlist: tuple[str, ...] | list[str] = (),
    level: int = 0,
) -> ModuleType:
    """Wrapper for :func:`__import__` that logs any import failures."""
    caller_frame = inspect.currentframe().f_back
    caller_module = caller_frame.f_globals.get("__name__", "<unknown>") if caller_frame else "<unknown>"
    try:
        return _original_import(name, globals, locals, fromlist, level)
    except Exception as exc:  # pragma: no cover - logging path
        logger.error(
            "Failed to import %s%s in %s: %s",
            name,
            f" from {', '.join(fromlist)}" if fromlist else "",
            caller_module,
            exc,
            exc_info=True,
        )
        raise


# Patch Python's import mechanism.
builtins.__import__ = _import_with_logging

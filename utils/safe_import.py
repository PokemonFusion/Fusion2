"""Fusion2 import helpers.

Use these in *our* code wherever we perform dynamic imports and want guaranteed
logging on failure, without touching third-party import behavior.
"""

from __future__ import annotations

import importlib
import logging
import sys
from contextlib import contextmanager
from typing import Any

log = logging.getLogger("fusion2.import")


def safe_import(dotted: str) -> Any:
    """Import ``dotted`` module, logging ``ModuleNotFoundError`` then re-raising."""

    try:
        return importlib.import_module(dotted)
    except ModuleNotFoundError:
        parts = dotted.split(".")
        if len(parts) > 1:
            parent_name = ".".join(parts[:-1])
            parent = sys.modules.get(parent_name)
            if parent is not None and getattr(parent, "__path__", None) == []:
                # ``parent`` may be a deliberately injected stub with an
                # empty ``__path__``. Temporarily remove it so Python can
                # attempt to import the real package, but restore the stub
                # if that still fails so callers (and test clean-up) see a
                # consistent module state.
                sys.modules.pop(parent_name, None)
                try:
                    return importlib.import_module(dotted)
                except ModuleNotFoundError:
                    sys.modules[parent_name] = parent
                    raise
        log.exception("Import failed: %s", dotted)
        raise


@contextmanager
def log_import_block(label: str):
    """Log ``ModuleNotFoundError`` occurring within the managed block."""

    try:
        yield
    except ModuleNotFoundError:  # pragma: no cover - logging path
        log.exception("Import failed in block: %s", label)
        raise


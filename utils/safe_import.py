"""Fusion2 import helpers.

Use these in *our* code wherever we perform dynamic imports and want guaranteed
logging on failure, without touching third-party import behavior.
"""
from __future__ import annotations

import importlib
import logging
from contextlib import contextmanager
from typing import Any

log = logging.getLogger("fusion2.import")


def safe_import(dotted: str) -> Any:
    """Import ``dotted`` module, logging ``ModuleNotFoundError`` then re-raising.

    Parameters
    ----------
    dotted : str
        Dotted path of the module to import.

    Returns
    -------
    Any
        The imported module.
    """
    try:
        return importlib.import_module(dotted)
    except ModuleNotFoundError:  # pragma: no cover - logging path
        log.exception("Import failed: %s", dotted)
        raise


@contextmanager
def log_import_block(label: str):
    """Log ``ModuleNotFoundError`` occurring within the managed block.

    Parameters
    ----------
    label : str
        Description for the import block, included in the log message.
    """
    try:
        yield
    except ModuleNotFoundError:  # pragma: no cover - logging path
        log.exception("Import failed in block: %s", label)
        raise

"""Callback resolution helpers for battle modules."""

from typing import Any
import importlib
import sys


def _resolve_callback(cb_name, registry: Any):
    """Return a callable referenced by ``cb_name`` from ``registry``.

    Parameters
    ----------
    cb_name:
        Either a callable or a string of the form ``"Class.method"``.
    registry:
        Module providing callback classes.

    Returns
    -------
    Callable | Any | None
        Resolved callable, the original ``cb_name`` if already callable,
        or ``None`` if resolution fails.
    """

    if not cb_name:
        return None
    if callable(cb_name):
        return cb_name
    if isinstance(cb_name, str):
        if registry is None:
            registry = sys.modules.get("pokemon.dex.functions.moves_funcs")
            if registry is None:
                try:  # pragma: no cover - optional lazy import
                    registry = importlib.import_module("pokemon.dex.functions.moves_funcs")
                except Exception:
                    return cb_name
        try:
            cls_name, func_name = cb_name.split(".", 1)
            cls = getattr(registry, cls_name, None)
            if cls:
                try:
                    obj = cls()
                except Exception:
                    obj = cls
                return getattr(obj, func_name, None)
        except Exception:
            return None
    return cb_name

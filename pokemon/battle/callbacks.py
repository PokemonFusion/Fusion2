"""Callback resolution helpers for battle modules."""

from typing import Any

from .registry import CALLBACK_REGISTRY


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
	return CALLBACK_REGISTRY.resolve_compat(cb_name, registry=registry)

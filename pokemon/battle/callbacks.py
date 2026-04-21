"""Callback resolution helpers for battle modules."""

from __future__ import annotations

import inspect
from typing import Any, Iterable

from utils.safe_import import safe_import

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


def resolve_callback_from_modules(
	cb_name: Any,
	module_paths: str | Iterable[str],
):
	"""Resolve ``cb_name`` against the first importable callback module."""

	if not cb_name:
		return None
	if isinstance(module_paths, str):
		module_paths = [module_paths]
	for module_path in module_paths:
		try:
			registry = safe_import(module_path)
		except Exception:
			continue
		callback = _resolve_callback(cb_name, registry)
		if callable(callback):
			return callback
	return CALLBACK_REGISTRY.resolve_compat(cb_name)


def invoke_callback(callback, *args, **kwargs):
	"""Call ``callback`` with permissive legacy arity fallback."""

	if not callable(callback):
		return None

	attempts: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
	if kwargs:
		attempts.append((args, kwargs))
		try:
			sig = inspect.signature(callback)
		except (TypeError, ValueError):
			sig = None
		if sig is not None:
			params = sig.parameters.values()
			if any(param.kind == inspect.Parameter.VAR_KEYWORD for param in params):
				filtered_kwargs = dict(kwargs)
			else:
				filtered_kwargs = {
					key: value
					for key, value in kwargs.items()
					if key in sig.parameters
				}
			attempts.append((args, filtered_kwargs))
			if not args and filtered_kwargs:
				attempts.append((tuple(), filtered_kwargs))
	if args:
		attempts.append((args, {}))
		for idx in range(len(args) - 1, -1, -1):
			attempts.append((args[:idx], {}))
	else:
		attempts.append((tuple(), {}))

	last_error: Exception | None = None
	for call_args, call_kwargs in attempts:
		try:
			return callback(*call_args, **call_kwargs)
		except TypeError as err:
			last_error = err
			continue

	if last_error is not None:
		raise last_error
	return callback()

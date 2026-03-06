"""Battle registries.

This module exposes:

* ``REGISTRY``: lightweight battle session registry used by handlers/commands.
* ``CALLBACK_REGISTRY``: typed callback registry that resolves compatibility
  string references once during registration.
"""

from __future__ import annotations

import sys
import weakref
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping

from utils.safe_import import safe_import


class _Registry:
    """Track active battle sessions."""

    def __init__(self) -> None:
        self._sessions: "weakref.WeakSet[object]" = weakref.WeakSet()

    def register(self, session) -> None:
        if session:
            self._sessions.add(session)

    def unregister(self, session) -> None:
        try:
            self._sessions.discard(session)
        except Exception:
            pass

    def all(self) -> List[object]:
        return list(self._sessions)

    def get_by_id(self, ident: str):
        for session in self._sessions:
            sid = (
                getattr(session, "id", None)
                or getattr(session, "uuid", None)
                or str(id(session))
            )
            if str(sid) == str(ident) or str(sid).endswith(str(ident).lstrip("#")):
                return session
        return None

    def sessions_for(self, caller) -> List[object]:
        out: List[object] = []
        for session in self._sessions:
            if caller in getattr(session, "teamA", []) or caller == getattr(
                session, "captainA", None
            ):
                out.append(session)
                continue
            if caller in getattr(session, "teamB", []) or caller == getattr(
                session, "captainB", None
            ):
                out.append(session)
                continue
            if caller in getattr(session, "observers", []):
                out.append(session)
        return out


REGISTRY = _Registry()

Callback = Callable[..., Any]


@dataclass(frozen=True)
class CallbackReference:
    """Normalized callback reference in ``ClassName.method`` format."""

    class_name: str
    method_name: str

    @classmethod
    def parse(cls, reference: str) -> "CallbackReference":
        """Parse ``reference`` formatted as ``ClassName.method_name``."""

        if "." not in reference:
            raise ValueError("Callback reference must be formatted as 'ClassName.method_name'.")
        class_name, method_name = reference.split(".", 1)
        if not class_name or not method_name:
            raise ValueError("Callback reference must include both class and method names.")
        return cls(class_name=class_name, method_name=method_name)


class CallbackRegistry:
    """Store validated, concrete callback callables."""

    def __init__(self) -> None:
        self._callbacks: Dict[str, Callback] = {}

    def register(self, key: str, callback: Any, *, registry: Any = None) -> Callback | None:
        """Register a callback under ``key``.

        ``callback`` may be a callable or a compatibility string reference.
        String references are validated and resolved once during registration.
        """

        resolved = self._resolve(callback, registry=registry)
        if resolved is None:
            self._callbacks.pop(key, None)
            return None
        self._callbacks[key] = resolved
        return resolved

    def get(self, key: str) -> Callback | None:
        """Return the callback registered for ``key`` if present."""

        return self._callbacks.get(key)

    def register_many(
        self,
        callbacks: Mapping[str, Any],
        *,
        registry: Any = None,
        key_prefix: str = "",
    ) -> Dict[str, Callback]:
        """Register many callbacks and return all successfully resolved entries."""

        registered: Dict[str, Callback] = {}
        for name, callback in callbacks.items():
            key = f"{key_prefix}{name}" if key_prefix else name
            resolved = self.register(key, callback, registry=registry)
            if resolved is not None:
                registered[key] = resolved
        return registered

    def resolve_compat(self, callback: Any, *, registry: Any = None) -> Callback | Any | None:
        """Compatibility resolver for call sites not yet migrated."""

        resolved = self._resolve(callback, registry=registry)
        if resolved is None:
            return callback if isinstance(callback, str) else None
        return resolved

    def _resolve(self, callback: Any, *, registry: Any = None) -> Callback | None:
        if callback is None:
            return None
        if callable(callback):
            return callback
        if not isinstance(callback, str):
            return None

        try:
            reference = CallbackReference.parse(callback)
        except ValueError:
            return None

        target_registry = registry or self._default_registry()
        if target_registry is None:
            return None

        cls = getattr(target_registry, reference.class_name, None)
        if cls is None:
            return None
        try:
            obj = cls()
        except Exception:
            obj = cls
        method = getattr(obj, reference.method_name, None)
        return method if callable(method) else None

    @staticmethod
    def _default_registry() -> Any:
        registry = sys.modules.get("pokemon.dex.functions.moves_funcs")
        if registry is not None:
            return registry
        try:  # pragma: no cover - optional lazy import
            return safe_import("pokemon.dex.functions.moves_funcs")
        except ModuleNotFoundError:  # pragma: no cover - optional dependency
            return None


CALLBACK_REGISTRY = CallbackRegistry()

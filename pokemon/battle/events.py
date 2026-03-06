"""Simple event dispatcher for battle callbacks."""

from __future__ import annotations

import inspect
from collections import defaultdict
from typing import Any, Callable, Dict, List

from .error_handling import handle_battle_exception


class EventDispatcher:
    """Dispatch named events to registered handlers."""

    def __init__(self, *, allow_arity_fallback: bool = False) -> None:
        self._handlers: Dict[str, List[Callable[..., Any]]] = defaultdict(list)
        self.allow_arity_fallback = allow_arity_fallback

    @staticmethod
    def _handler_identity(handler: Callable[..., Any]) -> str:
        """Return a stable debug identity for ``handler``."""

        module = getattr(handler, "__module__", None) or "<unknown-module>"
        qualname = getattr(handler, "__qualname__", None) or getattr(
            handler, "__name__", repr(handler)
        )
        return f"{module}.{qualname}"

    def register(self, event: str, handler: Callable[..., Any]) -> None:
        """Register ``handler`` to run when ``event`` is dispatched."""

        self._handlers[event].append(handler)

    def dispatch(self, event: str, **context: Any) -> List[Dict[str, Any]]:
        """Run all handlers registered for ``event`` with ``context``.

        Returns a list of structured failure payloads for callbacks that could
        not be executed. In fail-fast debug mode these exceptions are re-raised.
        """

        failures: List[Dict[str, Any]] = []
        battle = context.get("battle")
        pokemon = context.get("pokemon")
        for handler in list(self._handlers.get(event, [])):
            identity = self._handler_identity(handler)
            try:
                sig = inspect.signature(handler)
                if any(
                    p.kind == inspect.Parameter.VAR_KEYWORD
                    for p in sig.parameters.values()
                ):
                    params = context
                else:
                    params = {k: v for k, v in context.items() if k in sig.parameters}
                handler(**params)
            except Exception as err:
                fallback_error = None
                if self.allow_arity_fallback:
                    try:
                        handler()
                        continue
                    except Exception as fallback_err:
                        fallback_error = fallback_err
                failures.append(
                    handle_battle_exception(
                        battle=battle,
                        context="event_dispatch",
                        exception=fallback_error or err,
                        event=event,
                        pokemon=pokemon,
                        extra={
                            "handler": identity,
                            "event_name": event,
                            "initial_error": str(err),
                            "fallback_enabled": self.allow_arity_fallback,
                        },
                    )
                )
        return failures

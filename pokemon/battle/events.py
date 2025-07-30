"""Simple event dispatcher for battle callbacks."""
from collections import defaultdict
from typing import Callable, Dict, List, Any
import inspect


class EventDispatcher:
    """Dispatch named events to registered handlers."""

    def __init__(self) -> None:
        self._handlers: Dict[str, List[Callable[..., Any]]] = defaultdict(list)

    def register(self, event: str, handler: Callable[..., Any]) -> None:
        """Register ``handler`` to run when ``event`` is dispatched."""
        self._handlers[event].append(handler)

    def dispatch(self, event: str, **context: Any) -> None:
        """Run all handlers registered for ``event`` with ``context``."""
        for handler in list(self._handlers.get(event, [])):
            try:
                sig = inspect.signature(handler)
                if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
                    params = context
                else:
                    params = {k: v for k, v in context.items() if k in sig.parameters}
                handler(**params)
            except Exception:
                try:
                    handler()
                except Exception:
                    pass

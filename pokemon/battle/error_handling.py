"""Shared helpers for battle exception handling and fail-fast debug mode."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

logger = logging.getLogger("battle")


def battle_debug_fail_fast(battle: Any | None = None) -> bool:
    """Return ``True`` when battle exceptions should be re-raised.

    Fail-fast mode is enabled when any of these are true:
    - ``battle.debug`` is truthy.
    - ``battle.fail_fast_errors`` is truthy.
    - the process is running under pytest.
    - ``POKEMON_BATTLE_FAIL_FAST`` env var is explicitly set to ``1``/``true``.
    """

    if battle is not None:
        if bool(getattr(battle, "debug", False)):
            return True
        if bool(getattr(battle, "fail_fast_errors", False)):
            return True

    env = os.environ.get("POKEMON_BATTLE_FAIL_FAST", "").strip().lower()
    if env in {"1", "true", "yes", "on"}:
        return True
    return "PYTEST_CURRENT_TEST" in os.environ


def build_failure(
    *,
    battle: Any | None,
    context: str,
    exception: Exception,
    event: str | None = None,
    pokemon: Any | None = None,
    extra: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Create a structured failure payload for battle callback errors."""

    payload: Dict[str, Any] = {
        "ok": False,
        "context": context,
        "error_type": type(exception).__name__,
        "error": str(exception),
        "battle_id": getattr(battle, "battle_id", None) if battle is not None else None,
        "event": event,
        "pokemon": getattr(pokemon, "name", None) if pokemon is not None else None,
    }
    if extra:
        payload.update(extra)
    return payload


def handle_battle_exception(
    *,
    battle: Any | None,
    context: str,
    exception: Exception,
    event: str | None = None,
    pokemon: Any | None = None,
    extra: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Log a battle callback error and raise in fail-fast mode."""

    failure = build_failure(
        battle=battle,
        context=context,
        exception=exception,
        event=event,
        pokemon=pokemon,
        extra=extra,
    )
    logger.exception(
        "Battle callback failure [context=%s battle_id=%s event=%s pokemon=%s]",
        context,
        failure.get("battle_id"),
        failure.get("event"),
        failure.get("pokemon"),
    )
    if battle_debug_fail_fast(battle):
        raise
    return failure

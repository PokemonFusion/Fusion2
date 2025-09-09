"""Helpers for composing and validating Evennia lockstrings.

These utilities centralize how default room and exit locks are created and
validated. They include fallbacks so the website can still run even if Evennia
is not fully loaded (such as during collectstatic).
"""
from __future__ import annotations

from typing import Optional, Tuple

try:
    from evennia.locks.lockhandler import LockHandler, LockException
except Exception:  # pragma: no cover - used when Evennia isn't available
    class LockException(Exception):
        """Fallback lock exception."""

    class LockHandler:  # type: ignore
        """Minimal stand-in LockHandler used when Evennia isn't available."""

        def __init__(self, obj):
            self.obj = obj

        def add(self, lockstring: str):
            if not isinstance(lockstring, str) or ":" not in lockstring:
                raise LockException("Invalid lockstring")


def _owner_triple(user_id: int, caller_id: Optional[int]) -> str:
    """Return control/delete/edit locks for a given owner."""
    parts = [f"pid({user_id})", f"id({caller_id})" if caller_id else None, "perm(Admin)"]
    who = " or ".join(p for p in parts if p)
    return ";".join(f"{acc}:{who}" for acc in ("control", "delete", "edit"))


def compose_room_default(user_id: int, caller_id: Optional[int]) -> str:
    """Compose the default lockstring for a room."""
    owner = _owner_triple(user_id, caller_id)
    base = "get:false();puppet:false();teleport:false();teleport_here:true()"
    return f"{owner};{base}"


def compose_exit_default(
    user_id: int,
    caller_id: Optional[int],
    traverse_expr: str = "all()",
) -> str:
    """Compose the default lockstring for an exit."""
    owner = _owner_triple(user_id, caller_id)
    base = (
        f"puppet:false();traverse:{traverse_expr};get:false();"
        "teleport:false();teleport_here:false()"
    )
    return f"{owner};{base}"


def validate_lockstring(lockstring: str) -> Tuple[bool, str]:
    """Validate a lockstring using Evennia's parser."""
    dummy = type("Dummy", (), {})()
    dummy.locks = LockHandler(dummy)  # type: ignore[attr-defined]
    try:
        dummy.locks.add(lockstring)
        return True, "OK"
    except LockException as exc:  # pragma: no cover - simple exception handling
        return False, str(exc)


def apply_default_locks(
    obj,
    *,
    as_exit: bool,
    user_id: int,
    caller_id: Optional[int],
) -> None:
    """Apply stored default locks to ``obj``.

    If the ``LockDefaults`` model is unavailable or no default is stored,
    compose a fallback on the fly.
    """
    try:
        from ..models import LockDefaults  # type: ignore
        defaults = LockDefaults.get()
        raw = defaults.exit_default if as_exit else defaults.room_default
    except Exception:
        raw = ""
    if not raw:
        raw = (
            compose_exit_default(user_id, caller_id)
            if as_exit
            else compose_room_default(user_id, caller_id)
        )
    obj.locks.add(raw)

from __future__ import annotations
from typing import Optional
from django.conf import settings
try:
    from evennia.locks.lockhandler import LockHandler, LockException
except Exception:
    class LockException(Exception): ...
    class LockHandler:
        def __init__(self, obj): ...
        def add(self, lockstring: str):
            if not isinstance(lockstring, str) or ":" not in lockstring:
                raise LockException("Invalid lockstring")

ROOM_LOCK_BASE = getattr(
    settings,
    "ROOM_LOCK_BASE",
    "get:false();puppet:false();teleport:false();teleport_here:true()",
)
EXIT_LOCK_BASE = getattr(
    settings,
    "EXIT_LOCK_BASE",
    "puppet:false();traverse:all();get:false();teleport:false();teleport_here:false()",
)
INCLUDE_CREATOR_IN_OWNER = getattr(settings, "INCLUDE_CREATOR_IN_OWNER", True)

def _owner_triple(user_id: int, creator_id: Optional[int]) -> str:
    parts = [f"pid({user_id})", "perm(Admin)"]
    if INCLUDE_CREATOR_IN_OWNER and creator_id:
        parts.insert(1, f"id({creator_id})")
    who = " or ".join(parts)
    return ";".join(f"{acc}:{who}" for acc in ("control", "delete", "edit"))

def compose_room_default(user_id: int, creator_id: Optional[int]) -> str:
    return f"{_owner_triple(user_id, creator_id)};{ROOM_LOCK_BASE}"

def compose_exit_default(user_id: int, creator_id: Optional[int], traverse_expr: str = "all()") -> str:
    base = EXIT_LOCK_BASE.replace("traverse:all()", f"traverse:{traverse_expr}")
    return f"{_owner_triple(user_id, creator_id)};{base}"

def validate_lockstring(lockstring: str) -> tuple[bool, str]:
    dummy = type("Dummy", (), {})()
    dummy.locks = LockHandler(dummy)
    try:
        dummy.locks.add(lockstring)
        return True, "OK"
    except LockException as e:
        return False, str(e)

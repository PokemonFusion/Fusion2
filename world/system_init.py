from __future__ import annotations

import os
from typing import Any

from utils.safe_import import safe_import

_system_holder: Any | None = None


def get_system() -> Any:
    """Return a global system holder, creating it if missing."""
    global _system_holder
    if _system_holder is not None:
        return _system_holder
    try:  # pragma: no cover - Evennia may be unavailable in tests
        if os.getenv("PF2_NO_EVENNIA"):
            raise Exception("stub")
        evennia = safe_import("evennia")
        scripts = evennia.search_script("System")  # type: ignore[attr-defined]
        if scripts:
            _system_holder = scripts[0]
        else:
            _system_holder = evennia.create_script("typeclasses.scripts.Script", key="System")
    except Exception:  # pragma: no cover - fallback simple holder

        class _Holder:
            pass

        _system_holder = _Holder()
    return _system_holder


def at_server_start() -> None:
    """Ensure global game systems are attached on startup."""
    try:
        from utils.db_connection_hygiene import install_command_connection_hygiene

        install_command_connection_hygiene()
    except Exception:
        pass

    system = get_system()
    try:
        from pokemon.battle.handler import battle_handler

        system.battle_manager = battle_handler
    except Exception:
        pass

    try:
        from world.heartbeat import ensure_heartbeat_script

        ensure_heartbeat_script()
    except Exception:
        pass

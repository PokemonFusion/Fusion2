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
    """Ensure the battle manager is attached on startup."""
    system = get_system()
    try:
        from services.battle.manager import BattleManager
    except Exception:  # pragma: no cover - manager import failed
        return
    if not hasattr(system, "battle_manager"):
        system.battle_manager = BattleManager()

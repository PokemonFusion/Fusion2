from __future__ import annotations

import os
from typing import Any, Optional

from utils.safe_import import safe_import

try:  # pragma: no cover - Evennia may be absent in tests
    if os.getenv("PF2_NO_EVENNIA"):
        raise Exception("stub")
    evennia = safe_import("evennia")
    DefaultScript = evennia.DefaultScript  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - fallback
    class DefaultScript:  # type: ignore[no-redef]
        """Minimal stand-in for Evennia's ``DefaultScript``."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.db = type("DB", (), {})()
            self.ndb = type("NDB", (), {})()

        def stop(self) -> None:  # pragma: no cover - trivial stub
            pass


from .instance import BattleInstance


class BattleManager(DefaultScript):
    """Global manager maintaining active ``BattleInstance`` objects."""

    def at_script_creation(self) -> None:  # pragma: no cover - only called by Evennia
        self.persistent = True
        if not getattr(self.db, "next_id", None):
            self.db.next_id = 1
        if not getattr(self.ndb, "instances", None):
            self.ndb.instances = {}

    # ------------------------------------------------------------------
    # Instance management
    # ------------------------------------------------------------------
    def create(self, initiator, opponent: Optional[Any] = None) -> BattleInstance:
        """Create a new battle instance and register it."""
        battle_id = int(self.db.next_id or 1)
        self.db.next_id = (battle_id + 1) % 32768
        inst = BattleInstance()
        inst.at_script_creation()
        inst.setup(battle_id, getattr(initiator, "id", None))
        if opponent is not None:
            inst.db.state["p2"]["trainer_id"] = getattr(opponent, "id", None)
        self.ndb.instances[battle_id] = inst
        return inst

    def get(self, battle_id: int) -> Optional[BattleInstance]:
        """Return the battle instance for ``battle_id`` if active."""
        return self.ndb.instances.get(battle_id)

    def for_player(self, player) -> Optional[BattleInstance]:
        """Return the instance a player is involved in if any."""
        pid = getattr(player, "id", None)
        if pid is None:
            return None
        for inst in self.ndb.instances.values():
            p1 = inst.db.state.get("p1", {}).get("trainer_id")
            p2 = inst.db.state.get("p2", {}).get("trainer_id")
            if pid in {p1, p2}:
                return inst
        return None

    # ------------------------------------------------------------------
    # Watchers
    # ------------------------------------------------------------------
    def watch(self, battle_id: int, watcher) -> bool:
        inst = self.get(battle_id)
        if not inst:
            return False
        wid = getattr(watcher, "id", watcher)
        inst.add_watcher(int(wid))
        return True

    def unwatch(self, battle_id: int, watcher) -> bool:
        inst = self.get(battle_id)
        if not inst:
            return False
        wid = getattr(watcher, "id", watcher)
        inst.remove_watcher(int(wid))
        return True

    # ------------------------------------------------------------------
    # Termination and cleanup
    # ------------------------------------------------------------------
    def abort(self, battle_id: int) -> None:
        inst = self.get(battle_id)
        if not inst:
            return
        inst.invalidate()
        self.ndb.instances.pop(battle_id, None)

    def abort_request(self, battle_id: int, requester) -> bool:
        """Handle an abort request from ``requester`` for ``battle_id``."""
        inst = self.get(battle_id)
        if not inst:
            return False
        if inst.db.state.get("turn", 0) < 2:
            inst.invalidate()
            self.ndb.instances.pop(battle_id, None)
            return True
        rid = getattr(requester, "id", requester)
        inst.db.state.setdefault("log", []).append(f"{rid} forfeits.")
        return True

    def gc(self) -> None:
        """Garbage collect invalidated instances."""
        to_remove = [bid for bid, inst in self.ndb.instances.items() if getattr(inst.ndb, "invalidated", False)]
        for bid in to_remove:
            self.ndb.instances.pop(bid, None)

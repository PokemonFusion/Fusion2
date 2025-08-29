from __future__ import annotations

import os
import random
import time
from typing import Any, Dict, Optional

from utils.safe_import import safe_import

try:  # pragma: no cover - Evennia may be absent in tests
    if os.getenv("PF2_NO_EVENNIA"):
        raise Exception("stub")
    evennia = safe_import("evennia")
    DefaultScript = evennia.DefaultScript  # type: ignore[attr-defined]
    create_channel = evennia.create_channel  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - fallback stubs
    class DefaultScript:  # type: ignore[no-redef]
        """Minimal stand-in for Evennia's ``DefaultScript``."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.db = type("DB", (), {})()
            self.ndb = type("NDB", (), {})()

        def stop(self) -> None:  # pragma: no cover - trivial stub
            pass

    def create_channel(key: str, *_, **__) -> Any:  # type: ignore[misc]
        return type("Channel", (), {"key": key, "msg": lambda self, text, **kw: None})()


class BattleInstance(DefaultScript):
    """Script container for an individual battle."""

    def at_script_creation(self) -> None:  # pragma: no cover - only called by Evennia
        self.persistent = True

    def setup(self, battle_id: int, initiator_id: Optional[int] = None) -> None:
        """Populate initial state for the battle instance."""
        seed = random.randint(0, 2**31 - 1)
        now = time.time()
        self.db.state = {
            "id": battle_id,
            "rng_seed": seed,
            "started_at": now,
            "last_tick": now,
            "log": [],
            "watchers": [],
            "initiator_id": initiator_id,
            "p1": {
                "trainer_id": initiator_id,
                "party_snapshot": [],
                "active_index": 0,
                "side_effects": [],
            },
            "p2": {
                "trainer_id": None,
                "party_snapshot": [],
                "active_index": 0,
                "side_effects": [],
            },
            "queue": [],
            "turn": 0,
            "phase": "init",
            "weather": None,
            "terrain": None,
            "hazards": {"p1": [], "p2": []},
        }
        self.ndb.accounts: Dict[int, Any] = {}
        self.ndb.characters: Dict[int, Any] = {}
        self.ndb.speed_cache: Dict[str, Any] = {}
        try:  # pragma: no cover - channel support optional
            chan = create_channel(f"battle-{battle_id}")
            self.ndb.channel = chan
            self.ndb.prefix = f"[B#{battle_id}]"
        except Exception:
            self.ndb.channel = None
            self.ndb.prefix = f"[B#{battle_id}]"

    def add_watcher(self, watcher_id: int) -> None:
        """Register a watcher by id."""
        watchers = list(self.db.state.get("watchers", []))
        if watcher_id not in watchers:
            watchers.append(int(watcher_id))
            self.db.state["watchers"] = watchers

    def remove_watcher(self, watcher_id: int) -> None:
        """Remove a watcher by id."""
        watchers = list(self.db.state.get("watchers", []))
        if watcher_id in watchers:
            watchers.remove(int(watcher_id))
            self.db.state["watchers"] = watchers

    def msg(self, text: str) -> None:
        """Send ``text`` to the battle channel if available."""
        chan = getattr(self.ndb, "channel", None)
        prefix = getattr(self.ndb, "prefix", "")
        if chan and hasattr(chan, "msg"):
            chan.msg(f"{prefix} {text}")

    def invalidate(self) -> None:
        """Invalidate the battle without persisting further state."""
        self.ndb.invalidated = True
        try:
            self.stop()
        except Exception:  # pragma: no cover - stop may not exist
            pass

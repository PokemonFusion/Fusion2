from __future__ import annotations

import os
import random
import time
from typing import Any, Dict, Optional

from pokemon.battle.watchers import notify_watchers
from utils.locks import clear_battle_lock

try:  # pragma: no cover - model import may fail during tests
    from pokemon.models.core import BattleSlot
except Exception:  # pragma: no cover - fallback when Django isn't ready
    BattleSlot = None  # type: ignore

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
        self.rng = random.Random(seed)
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
        # Expose the RNG on ``ndb`` so other components can access it
        self.ndb.rng = self.rng
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
        message = f"{prefix} {text}" if prefix else text
        if chan and hasattr(chan, "msg"):
            chan.msg(message)
        notify_watchers(self.db.state, message)

    def invalidate(self) -> None:
        """Invalidate the battle without persisting further state."""
        for char in list(getattr(self.ndb, "characters", {}).values()):
            try:
                clear_battle_lock(char)
            except Exception:
                pass
            ndb = getattr(char, "ndb", None)
            if ndb and getattr(ndb, "battle_instance", None) is self:
                try:
                    delattr(ndb, "battle_instance")
                except Exception:
                    pass
            db = getattr(char, "db", None)
            if db and hasattr(db, "battle_id"):
                try:
                    delattr(db, "battle_id")
                except Exception:
                    pass
        self.ndb.invalidated = True
        try:
            self.stop()
        except Exception:  # pragma: no cover - stop may not exist
            pass

    # ------------------------------------------------------------------
    # Slot synchronisation
    # ------------------------------------------------------------------
    def _sync_slots(self) -> None:
        """Mirror active Pokémon state to ``BattleSlot`` rows.

        The game state keeps snapshots for each participant's party.  This
        helper updates or creates ``BattleSlot`` entries for the currently
        active Pokémon on both sides and removes stale rows for this battle.
        It is tolerant to missing database connections to remain test friendly.
        """

        if BattleSlot is None:
            return

        battle_id = self.db.state.get("id")
        active_ids = []
        for team_key, team_idx in (("p1", 1), ("p2", 2)):
            team = self.db.state.get(team_key, {})
            party = team.get("party_snapshot", [])
            active_index = int(team.get("active_index", 0))
            if 0 <= active_index < len(party):
                mon = party[active_index]
                uid = mon.get("unique_id")
                if not uid:
                    continue
                active_ids.append(uid)
                try:
                    BattleSlot.objects.update_or_create(
                        pokemon_id=uid,
                        defaults={
                            "battle_id": battle_id,
                            "battle_team": team_idx,
                            "current_hp": mon.get("current_hp", 0),
                            "status": mon.get("status", ""),
                            "fainted": bool(mon.get("fainted", False)),
                        },
                    )
                except Exception:  # pragma: no cover - database errors are ignored
                    continue
        if active_ids:
            try:
                BattleSlot.objects.filter(battle_id=battle_id).exclude(
                    pokemon_id__in=active_ids
                ).delete()
            except Exception:  # pragma: no cover - database errors are ignored
                pass

    def touch(self) -> None:
        """Update ``last_tick`` timestamp and sync active slots."""

        self.db.state["last_tick"] = time.time()
        self._sync_slots()

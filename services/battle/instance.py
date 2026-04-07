from __future__ import annotations

import os
import random
import time
import logging
from typing import Any, Dict, List, Literal, Optional, TypedDict, cast

try:  # pragma: no cover - Django may be unavailable in lightweight test envs
    from django.db import DatabaseError
except Exception:  # pragma: no cover - intentional boundary catch for optional Django dependency
    class DatabaseError(Exception):
        """Fallback database error type when Django is unavailable."""

from pokemon.battle.watchers import notify_watchers
from utils.locks import clear_battle_lock

try:  # pragma: no cover - model import may fail during tests
    from pokemon.models.core import BattleSlot
except Exception:  # pragma: no cover - intentional boundary catch when Django apps aren't loaded
    BattleSlot = None  # type: ignore

from utils.safe_import import safe_import

try:  # pragma: no cover - Evennia may be absent in tests
    if os.getenv("PF2_NO_EVENNIA"):
        raise Exception("stub")
    evennia = safe_import("evennia")
    DefaultScript = evennia.DefaultScript  # type: ignore[attr-defined]
    create_channel = evennia.create_channel  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - intentional boundary catch for optional Evennia dependency
    class DefaultScript:  # type: ignore[no-redef]
        """Minimal stand-in for Evennia's ``DefaultScript``."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.db = type("DB", (), {})()
            self.ndb = type("NDB", (), {})()

        def stop(self) -> None:  # pragma: no cover - trivial stub
            pass

    def create_channel(key: str, *_, **__) -> Any:  # type: ignore[misc]
        return type("Channel", (), {"key": key, "msg": lambda self, text, **kw: None})()

logger = logging.getLogger(__name__)


class PlayerSideState(TypedDict):
    """Runtime state for one battle side."""

    trainer_id: Optional[int]
    party_snapshot: List[Dict[str, Any]]
    active_index: int
    side_effects: List[str]


class HazardsState(TypedDict):
    """Hazards currently active on each side."""

    p1: List[str]
    p2: List[str]


class QueueEntry(TypedDict, total=False):
    """A queued battle command entry."""

    player_id: int
    action: Literal["move", "switch", "item", "run", "pass"]
    move: str
    target: str
    slot: int
    item: str
    priority: int
    speed: int


class BattleMetadata(TypedDict):
    """Top-level battle metadata and timing fields."""

    id: int
    rng_seed: int
    started_at: float
    last_tick: float
    log: List[str]
    watchers: List[int]
    initiator_id: Optional[int]
    turn: int
    phase: str
    weather: Optional[str]
    terrain: Optional[str]


class BattleState(BattleMetadata):
    """Persisted script state payload for a battle instance."""

    p1: PlayerSideState
    p2: PlayerSideState
    queue: List[QueueEntry]
    hazards: HazardsState


def build_initial_state(
    battle_id: int, initiator_id: Optional[int], now: float, rng_seed: int
) -> BattleState:
    """Build the persisted initial state for a newly created battle."""

    return {
        "id": battle_id,
        "rng_seed": rng_seed,
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


class BattleInstance(DefaultScript):
    """Script container for an individual battle."""

    def at_script_creation(self) -> None:  # pragma: no cover - only called by Evennia
        self.persistent = True

    def setup(self, battle_id: int, initiator_id: Optional[int] = None) -> None:
        """Populate initial state for the battle instance."""
        seed = random.randint(0, 2**31 - 1)
        self.rng = random.Random(seed)
        now = time.time()
        self.db.state = build_initial_state(
            battle_id=battle_id, initiator_id=initiator_id, now=now, rng_seed=seed
        )
        self.ndb.accounts: Dict[int, Any] = {}
        self.ndb.characters: Dict[int, Any] = {}
        self.ndb.speed_cache: Dict[str, Any] = {}
        # Expose the RNG on ``ndb`` so other components can access it
        self.ndb.rng = self.rng
        try:  # pragma: no cover - channel support optional
            chan = create_channel(f"battle-{battle_id}")
            self.ndb.channel = chan
            self.ndb.prefix = f"[B#{battle_id}]"
        except (AttributeError, TypeError):
            logger.debug("Battle channel unavailable; using watcher-only messaging.", exc_info=True)
            self.ndb.channel = None
            self.ndb.prefix = f"[B#{battle_id}]"

    @property
    def state(self) -> BattleState:
        """Return battle state with a typed view."""

        return cast(BattleState, self.db.state)

    @property
    def p1(self) -> PlayerSideState:
        """Typed helper for player one side state."""

        return self.state["p1"]

    @property
    def p2(self) -> PlayerSideState:
        """Typed helper for player two side state."""

        return self.state["p2"]

    @property
    def turn(self) -> int:
        """Current turn number."""

        return int(self.state.get("turn", 0))

    @turn.setter
    def turn(self, value: int) -> None:
        """Set the current turn number."""

        self.state["turn"] = int(value)

    @property
    def watchers(self) -> List[int]:
        """Watcher ids registered for the battle."""

        return self.state["watchers"]

    def add_watcher(self, watcher_id: int) -> None:
        """Register a watcher by id."""
        watchers = list(self.watchers)
        if watcher_id not in watchers:
            watchers.append(int(watcher_id))
            self.state["watchers"] = watchers

    def remove_watcher(self, watcher_id: int) -> None:
        """Remove a watcher by id."""
        watchers = list(self.watchers)
        if watcher_id in watchers:
            watchers.remove(int(watcher_id))
            self.state["watchers"] = watchers

    def msg(self, text: str) -> None:
        """Send ``text`` to the battle channel if available."""
        chan = getattr(self.ndb, "channel", None)
        prefix = getattr(self.ndb, "prefix", "")
        message = f"{prefix} {text}" if prefix else text
        if chan and hasattr(chan, "msg"):
            chan.msg(message)
        notify_watchers(self.state, message)

    def invalidate(self) -> None:
        """Invalidate the battle without persisting further state."""
        for char in list(getattr(self.ndb, "characters", {}).values()):
            try:
                clear_battle_lock(char)
            except (AttributeError, TypeError):
                logger.debug("Failed to clear battle lock for character during invalidate.", exc_info=True)
            ndb = getattr(char, "ndb", None)
            if ndb and getattr(ndb, "battle_instance", None) is self:
                try:
                    delattr(ndb, "battle_instance")
                except (AttributeError, TypeError):
                    logger.debug("Could not remove battle_instance from character ndb.", exc_info=True)
            db = getattr(char, "db", None)
            if db and hasattr(db, "battle_id"):
                try:
                    delattr(db, "battle_id")
                except (AttributeError, TypeError):
                    logger.debug("Could not remove battle_id from character db.", exc_info=True)
        self.ndb.invalidated = True
        try:
            self.stop()
        except AttributeError:  # pragma: no cover - stop may not exist
            logger.debug("BattleInstance.stop unavailable during invalidate.", exc_info=True)

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

        battle_id = self.state.get("id")
        active_ids = []
        for team_key, team_idx in (("p1", 1), ("p2", 2)):
            team = self.state.get(team_key, {})
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
                except DatabaseError:  # pragma: no cover - database errors are ignored
                    logger.debug("Failed to update BattleSlot during sync.", exc_info=True)
                    continue
        if active_ids:
            try:
                BattleSlot.objects.filter(battle_id=battle_id).exclude(
                    pokemon_id__in=active_ids
                ).delete()
            except DatabaseError:  # pragma: no cover - database errors are ignored
                logger.debug("Failed to prune stale BattleSlot rows.", exc_info=True)

    def touch(self) -> None:
        """Update ``last_tick`` timestamp and sync active slots."""

        self.state["last_tick"] = time.time()
        self._sync_slots()

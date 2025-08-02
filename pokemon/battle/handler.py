from __future__ import annotations

from typing import Dict, TYPE_CHECKING

try:
    from evennia.utils.logger import log_info
except Exception:  # pragma: no cover - fallback if Evennia not available
    import logging
    _log = logging.getLogger(__name__)

    def log_info(*args, **kwargs):
        _log.info(*args, **kwargs)

from evennia import search_object
from evennia.server.models import ServerConfig
from .storage import BattleDataWrapper

if TYPE_CHECKING:
    from .battleinstance import BattleSession


class BattleHandler:
    """Track and persist active battle instances."""

    def __init__(self):
        # map active battle_id -> BattleSession
        self.instances: Dict[int, BattleSession] = {}

    # -------------------------------------------------------------
    # ID generation
    # -------------------------------------------------------------
    def next_id(self) -> int:
        """Return the next unique battle id."""
        current = ServerConfig.objects.conf("next_battle_id", default=1)
        ServerConfig.objects.conf(key="next_battle_id", value=current + 1)
        return current

    # -------------------------------------------------------------
    # Persistence helpers
    # -------------------------------------------------------------
    def _save(self) -> None:
        """Persist the current active battle ids and their rooms."""
        data = {bid: inst.room.id for bid, inst in self.instances.items()}
        ServerConfig.objects.conf(key="active_battle_rooms", value=data)

    def restore(self) -> None:
        """Reload any battle instances stored on the server."""
        mapping = ServerConfig.objects.conf("active_battle_rooms", default={})
        from .battleinstance import BattleSession
        for bid, rid in mapping.items():
            rooms = search_object(f"#{rid}")
            if not rooms:
                continue
            room = rooms[0]
            try:
                inst = BattleSession.restore(room, int(bid))
            except Exception:
                continue
            if inst:
                self.instances[int(bid)] = inst
        self._save()

    def save(self) -> None:
        """Persist the currently tracked instances."""
        self._save()

    def clear(self) -> None:
        """Remove all tracked battle instances."""
        self.instances.clear()
        ServerConfig.objects.conf(key="active_battle_rooms", delete=True)

    # -------------------------------------------------------------
    # Management API
    # -------------------------------------------------------------
    def register(self, inst: BattleSession) -> None:
        """Track the given battle session."""
        self.instances[inst.battle_id] = inst
        self._save()

    def unregister(self, inst: BattleSession) -> None:
        bid = inst.battle_id
        if bid in self.instances:
            del self.instances[bid]
            self._save()

    # -------------------------------------------------------------
    # Reload helpers
    # -------------------------------------------------------------
    def rebuild_ndb(self) -> None:
        """Repopulate ndb attributes for all tracked battle instances."""
        from .battleinstance import BattleSession

        log_info(f"Rebuilding ndb data for {len(self.instances)} active battles")
        for inst in list(self.instances.values()):
            battle_instances = getattr(inst.room.ndb, "battle_instances", None)
            if not battle_instances or not hasattr(battle_instances, "__setitem__"):
                battle_instances = {}
                inst.room.ndb.battle_instances = battle_instances
            battle_instances[inst.battle_id] = inst

            room_key = getattr(inst.room, "key", inst.room.id)
            log_info(
                f"Restored battle {inst.battle_id} in room '{room_key}' (#" f"{inst.room.id})"
            )

            # rebuild live logic from stored room data if needed
            if not inst.logic:
                storage = BattleDataWrapper(inst.room, inst.battle_id)
                data = storage.get("data")
                state = storage.get("state")
                if data is not None or state is not None or storage.get("logic") is not None:
                    from .battleinstance import BattleLogic

                    if data is None or state is None:
                        logic_info = storage.get("logic", {}) or {}
                        data = data or logic_info.get("data")
                        state = state or logic_info.get("state")
                    inst.logic = BattleLogic.from_dict({"data": data, "state": state})
                    inst.logic.battle.log_action = inst.notify
                    inst.temp_pokemon_ids = list(storage.get("temp_pokemon_ids") or [])
                inst.storage = storage

            for obj in inst.trainers + list(inst.observers):
                if obj:
                    obj.ndb.battle_instance = inst


battle_handler = BattleHandler()

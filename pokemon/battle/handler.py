from __future__ import annotations

from typing import Dict, List, TYPE_CHECKING

from evennia import search_object
from evennia.server.models import ServerConfig

if TYPE_CHECKING:
    from .battleinstance import BattleInstance


class BattleHandler:
    """Track and persist active battle instances."""

    def __init__(self):
        self.instances: Dict[int, BattleInstance] = {}

    # -------------------------------------------------------------
    # Persistence helpers
    # -------------------------------------------------------------
    def _save(self) -> None:
        """Persist the current list of active battle room ids."""
        ServerConfig.objects.conf(
            key="active_battle_rooms", value=list(self.instances.keys())
        )

    def restore(self) -> None:
        """Reload any battle instances stored on the server."""
        ids: List[int] = ServerConfig.objects.conf(
            "active_battle_rooms", default=[]
        )
        from .battleinstance import BattleInstance
        for rid in ids:
            rooms = search_object(rid)
            if not rooms:
                continue
            room = rooms[0]
            try:
                inst = BattleInstance.restore(room)
            except Exception:
                continue
            if inst:
                self.instances[rid] = inst
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
    def register(self, inst: BattleInstance) -> None:
        self.instances[inst.room.id] = inst
        self._save()

    def unregister(self, inst: BattleInstance) -> None:
        rid = inst.room.id
        if rid in self.instances:
            del self.instances[rid]
            self._save()


battle_handler = BattleHandler()

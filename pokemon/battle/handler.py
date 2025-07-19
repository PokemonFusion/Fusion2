from __future__ import annotations

from typing import Dict, TYPE_CHECKING

from evennia import search_object
from evennia.server.models import ServerConfig

if TYPE_CHECKING:
    from .battleinstance import BattleInstance


class BattleHandler:
    """Track and persist active battle instances."""

    def __init__(self):
        self.instances: Dict[int, BattleInstance] = {}

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
        """Persist the current active battle rooms and ids."""
        data = {rid: inst.battle_id for rid, inst in self.instances.items()}
        ServerConfig.objects.conf(key="active_battle_rooms", value=data)

    def restore(self) -> None:
        """Reload any battle instances stored on the server."""
        mapping = ServerConfig.objects.conf("active_battle_rooms", default={})
        from .battleinstance import BattleInstance
        for rid, bid in mapping.items():
            rooms = search_object(rid)
            if not rooms:
                continue
            room = rooms[0]
            try:
                inst = BattleInstance.restore(room, bid)
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

    # -------------------------------------------------------------
    # Reload helpers
    # -------------------------------------------------------------
    def rebuild_ndb(self) -> None:
        """Repopulate ndb attributes for all tracked battle instances."""
        from .battleinstance import BattleInstance

        for inst in list(self.instances.values()):
            battle_instances = getattr(inst.room.ndb, "battle_instances", None)
            if not isinstance(battle_instances, dict):
                battle_instances = {}
                inst.room.ndb.battle_instances = battle_instances
            battle_instances[inst.battle_id] = inst

            # rebuild live logic from stored room data if needed
            if not inst.logic:
                data_map = getattr(inst.room.db, "battle_data", {})
                entry = data_map.get(inst.battle_id)
                if entry:
                    from .battleinstance import BattleLogic

                    inst.logic = BattleLogic.from_dict(entry.get("logic", entry))
                    inst.temp_pokemon_ids = list(entry.get("temp_pokemon_ids", []))

            for obj in inst.trainers + list(inst.observers):
                if obj:
                    obj.ndb.battle_instance = inst


battle_handler = BattleHandler()

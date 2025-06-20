from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict

from evennia import search_object

from .battleinstance import BattleInstance

@dataclass
class PvpRequest:
    host: object
    password: Optional[str] = None
    how_many: int = 1
    team_size: int = 6
    opponent: Optional[object] = None
    room_id: int = 0

    def to_dict(self) -> Dict:
        return {
            "host": self.host.id,
            "password": self.password,
            "how_many": self.how_many,
            "team_size": self.team_size,
            "opponent": self.opponent.id if self.opponent else None,
            "room_id": self.room_id,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "PvpRequest":
        host = search_object(data["host"])[0] if data.get("host") else None
        opp = search_object(data["opponent"])[0] if data.get("opponent") else None
        obj = cls(host=host, password=data.get("password"), how_many=data.get("how_many", 1), team_size=data.get("team_size", 6), opponent=opp)
        obj.room_id = data.get("room_id", 0)
        return obj


def start_pvp_battle(request: PvpRequest) -> Optional[BattleInstance]:
    """Start a PVP battle from an accepted request."""

    if not request.host or not request.opponent:
        return None

    inst = BattleInstance(request.host)
    inst.start_pvp(request.opponent)
    request.host.ndb.pvp_request = None
    request.opponent.ndb.pvp_request = None
    return inst

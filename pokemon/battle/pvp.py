"""Simple PVP battle request system.

This module implements a very small subset of the MUF-based PVP logic
found in ``reference_material/battletypes.txt``. It allows players to
create PVP requests, join them and start a battle using the existing
``BattleSession`` helper.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class PVPRequest:
    """Represents a pending PVP request in a room."""

    host_id: int
    host_key: str
    password: Optional[str] = None
    opponent_id: Optional[int] = None

    def get_host(self):
        """Return the host object if available."""
        try:
            from evennia import search_object

            return search_object(f"#{self.host_id}")[0]
        except Exception:
            return None

    def get_opponent(self):
        """Return the opponent object if available."""
        if self.opponent_id is None:
            return None
        try:
            from evennia import search_object

            return search_object(f"#{self.opponent_id}")[0]
        except Exception:
            return None

    def is_joinable(self) -> bool:
        """Return ``True`` if this request can be joined."""
        return self.opponent_id is None


def get_requests(location) -> Dict[int, PVPRequest]:
    """Return mapping of host id -> request on the location."""
    reqs = location.db.pvp_requests
    if not reqs:
        reqs = {}
        location.db.pvp_requests = reqs
    return reqs


def create_request(host, password: Optional[str] = None) -> PVPRequest:
    """Create a new request on the host's location."""
    reqs = get_requests(host.location)
    if host.id in reqs:
        raise ValueError("You are already hosting a PVP request.")
    req = PVPRequest(host_id=host.id, host_key=host.key, password=password)
    reqs[host.id] = req
    # persist after mutation
    host.location.db.pvp_requests = reqs

    # lock the host in place until the request is resolved
    if hasattr(host, "db"):
        host.db.pvp_locked = True

    # announce the request to the room
    loc = getattr(host, "location", None)
    if loc:
        try:
            loc.msg_contents(
                f"{host.key} has created a PVP request. Use |w+pvp/join {host.key}|n to accept."
            )
        except Exception:
            pass

    return req


def remove_request(host) -> None:
    reqs = get_requests(host.location)
    reqs.pop(host.id, None)
    host.location.db.pvp_requests = reqs
    if hasattr(host, "db"):
        host.db.pvp_locked = False


def find_request(location, host_name: str) -> Optional[PVPRequest]:
    for req in get_requests(location).values():
        if req.host_key.lower().startswith(host_name.lower()):
            return req
    return None



def start_pvp_battle(host, opponent) -> None:
    """Create and start a PVP ``BattleSession`` between ``host`` and ``opponent``."""
    from .battleinstance import BattleSession

    battle = BattleSession(host, opponent)
    battle.start_pvp()


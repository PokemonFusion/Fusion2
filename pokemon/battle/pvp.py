"""Simple PVP battle request system.

This module implements a very small subset of the MUF-based PVP logic
found in ``reference_material/battletypes.txt``. It allows players to
create PVP requests, join them and start a battle using the existing
``BattleInstance`` helper.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class PVPRequest:
    """Represents a pending PVP request in a room."""

    host: object
    password: Optional[str] = None
    opponent: Optional[object] = None

    def is_joinable(self, password: Optional[str] = None) -> bool:
        if self.opponent:
            return False
        if self.password and self.password != password:
            return False
        return True


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
    req = PVPRequest(host=host, password=password)
    reqs[host.id] = req
    return req


def remove_request(host) -> None:
    reqs = get_requests(host.location)
    reqs.pop(host.id, None)


def find_request(location, host_name: str) -> Optional[PVPRequest]:
    for req in get_requests(location).values():
        if req.host.key.lower().startswith(host_name.lower()):
            return req
    return None



def start_pvp_battle(host, opponent) -> None:
    """Create and start a PVP ``BattleInstance`` between ``host`` and ``opponent``."""
    from .battleinstance import BattleInstance

    battle = BattleInstance(host, opponent)
    battle.start_pvp()


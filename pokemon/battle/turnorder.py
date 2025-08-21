"""Determine the order of actions for a battle turn."""

from __future__ import annotations

import random
from typing import List

from utils.safe_import import safe_import

try:
    MOVEDEX = safe_import("pokemon.dex").MOVEDEX  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover - dex may be unavailable in tests
    MOVEDEX = {}

try:  # pragma: no cover - fallback when engine not available
    _normalize_key = safe_import("pokemon.battle.engine")._normalize_key  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover
    def _normalize_key(name: str) -> str:
        return name.replace(" ", "").replace("-", "").replace("'", "").lower()

from .battledata import TurnInit


class _Priority:
    """Internal helper for ordering."""

    priorities: List[int] = []

    def __init__(self, turndata: TurnInit, pokemon):
        pokemon.tempvals.clear()
        if turndata.switch is not None:
            self.priority = 6
        elif turndata.run is not None:
            self.priority = 9
        elif turndata.item is not None:
            self.priority = 8
        elif turndata.recharge is not None:
            self.priority = 6
        elif turndata.attack:
            move_entry = MOVEDEX.get(_normalize_key(turndata.attack.move))
            self.priority = (
                getattr(move_entry, "raw", {}).get("priority", 0)
                if move_entry
                else 0
            )
        else:
            self.priority = 0

        self.priorities.append(self.priority)
        self.speed = getattr(pokemon, "speed", 0) + random.uniform(0.0, 0.1)

    @classmethod
    def max(cls) -> int:
        return max(cls.priorities) if cls.priorities else 0

    @classmethod
    def min(cls) -> int:
        return min(cls.priorities) if cls.priorities else 0


def calculateTurnorder(battleround) -> List[str]:
    """Return the resolution order for the given turn."""

    _Priority.priorities.clear()
    priorities = {
        key: _Priority(pos.turninit, pos.pokemon)
        for key, pos in battleround.positions.items()
    }

    turnorder: List[str] = []
    for pri in range(_Priority.max(), _Priority.min() - 1, -1):
        if len(turnorder) == len(priorities):
            break
        current = [pos for pos, data in priorities.items() if data.priority == pri]
        if not current:
            continue
        current.sort(key=lambda x: priorities[x].speed, reverse=True)
        turnorder.extend(current)

    return turnorder

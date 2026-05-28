"""Pure data structures for PF2 spawn selection."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class SpawnEntry:
    species_id: str
    frequency: str
    band: int
    enabled: bool = True


@dataclass(frozen=True)
class SpawnChart:
    area_key: str
    entries: list[SpawnEntry]


@dataclass(frozen=True)
class SpawnContext:
    area_key: str
    band: int
    rng: Optional[random.Random] = None


@dataclass
class RotationBucket:
    queued: list[str] = field(default_factory=list)
    active: list[str] = field(default_factory=list)
    used: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SpawnRollResult:
    species_id: str
    frequency: str
    band: int
    level: int

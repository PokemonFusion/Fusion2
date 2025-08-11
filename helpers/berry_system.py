from __future__ import annotations

"""Simple berry planting and growth helpers."""

from dataclasses import dataclass


@dataclass
class BerryPlant:
    """Track a single berry plant's growth state."""

    berry: str
    growth_time: int = 3600  # seconds per stage
    stage: int = 0
    elapsed: int = 0
    waterings: int = 0
    max_stage: int = 4
    max_waterings: int = 4

    def progress(self, seconds: int) -> None:
        """Advance time by ``seconds`` and update growth stage."""
        self.elapsed += seconds
        while self.stage < self.max_stage and self.elapsed >= self.growth_time * (self.stage + 1):
            self.stage += 1

    def water(self) -> None:
        """Water this plant to increase its yield."""
        if self.waterings < self.max_waterings:
            self.waterings += 1

    def is_ready(self) -> bool:
        """Return True if berries can be harvested."""
        return self.stage >= self.max_stage

    def harvest(self) -> int:
        """Harvest berries and reset the plant. Return the yield."""
        if not self.is_ready():
            return 0
        yield_amount = 1 + self.waterings
        self.stage = 0
        self.elapsed = 0
        self.waterings = 0
        return yield_amount

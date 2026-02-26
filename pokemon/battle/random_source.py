"""Random source protocol used across battle simulation logic."""

from __future__ import annotations

import random
from typing import Protocol, runtime_checkable


@runtime_checkable
class RandomSource(Protocol):
    """Interface for deterministic random number generation in battles."""

    def random(self) -> float:
        """Return a random float in the half-open interval ``[0.0, 1.0)``."""

    def randint(self, a: int, b: int) -> int:
        """Return a random integer ``N`` such that ``a <= N <= b``."""

    def choice(self, seq):
        """Return a random element from *seq*."""

    def uniform(self, a: float, b: float) -> float:
        """Return a random float ``N`` such that ``a <= N <= b``."""

    def choices(self, population, weights=None, *, cum_weights=None, k: int = 1):
        """Return ``k`` weighted selections from *population*."""


def resolve_rng(*, battle=None, rng: RandomSource | None = None) -> RandomSource:
    """Resolve an RNG from explicit argument, then battle, then module random."""

    if rng is not None:
        return rng
    if battle is not None:
        battle_rng = getattr(battle, "rng", None)
        if battle_rng is not None:
            return battle_rng
    return random

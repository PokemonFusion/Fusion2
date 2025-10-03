"""Capture chance helpers for wild Pokémon encounters."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CaptureOutcome:
        """Result metadata returned from :func:`attempt_capture` when requested."""

        caught: bool
        shakes: int
        critical: bool

STATUS_MODIFIERS = {
        "slp": 2.5,
        "frz": 2.5,
        "par": 1.5,
	"brn": 1.5,
	"psn": 1.5,
	"tox": 1.5,
}


def attempt_capture(
        max_hp: int,
        current_hp: int,
        catch_rate: int,
        *,
        ball_modifier: float = 1.0,
        status: Optional[str] = None,
        rng: Optional[random.Random] = None,
        critical_chance: Optional[float] = None,
        return_details: bool = False,
) -> bool | CaptureOutcome:
        """Return ``True`` when a capture succeeds and ``False`` otherwise.

        When ``return_details`` is ``True`` a :class:`CaptureOutcome` instance is
        returned containing the success flag, the number of completed shakes and
        whether the attempt was a critical capture.
        """

        rng = rng or random
        status_key = (status or "").lower()
        status_mod = STATUS_MODIFIERS.get(status_key, 1.0)

        a = math.floor(((3 * max_hp - 2 * current_hp) * catch_rate * ball_modifier * status_mod) / (3 * max_hp))
        a = max(1, a)

        if a >= 255:
                outcome = CaptureOutcome(caught=True, shakes=4, critical=False)
                return outcome if return_details else True

        b = int(65536 / ((255 / a) ** 0.1875))
        chance = 0.0 if critical_chance is None else max(0.0, min(1.0, float(critical_chance)))
        is_critical = bool(chance and rng.random() < chance)
        shakes_required = 1 if is_critical else 4

        shakes_completed = 0
        for _ in range(shakes_required):
                if rng.randint(0, 65535) >= b:
                        outcome = CaptureOutcome(caught=False, shakes=shakes_completed, critical=is_critical)
                        return outcome if return_details else False
                shakes_completed += 1

        outcome = CaptureOutcome(caught=True, shakes=shakes_required, critical=is_critical)
        return outcome if return_details else True


__all__ = ["CaptureOutcome", "attempt_capture"]

"""Adapter-backed wild battle test helpers for staff-only commands."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from pokemon.battle.battleinstance import BattleSession

from .constants import SPAWN_BANDS
from .schema import SpawnChart, SpawnRollResult
from .selection import roll_spawn


DEFAULT_SPAWN_HUNT_TEST_BAND = 1


class SpawnHuntTestError(ValueError):
    """Raised when a spawn hunt test cannot be started cleanly."""


@dataclass(frozen=True)
class SpawnHuntTestResult:
    roll: SpawnRollResult
    battle_id: int


def parse_hunttest_band(raw_args: str | None) -> int:
    parts = (raw_args or "").split()
    if len(parts) > 1:
        raise ValueError("Usage: @spawnhunttest [band]")
    if not parts:
        return DEFAULT_SPAWN_HUNT_TEST_BAND
    try:
        band = int(parts[0])
    except ValueError as exc:
        raise ValueError("Band must be a number from 1 to 4.") from exc
    if band not in SPAWN_BANDS:
        raise ValueError("Band must be a number from 1 to 4.")
    return band


def active_battle_for(caller, battle_session_cls=BattleSession):
    ensure_for_player = getattr(battle_session_cls, "ensure_for_player", None)
    if callable(ensure_for_player):
        try:
            active = ensure_for_player(caller)
        except Exception:
            active = None
        if active:
            return active

    ndb = getattr(caller, "ndb", None)
    active = getattr(ndb, "battle_instance", None)
    if active:
        return active
    db = getattr(caller, "db", None)
    battle_id = getattr(db, "battle_id", None)
    if battle_id is not None:
        return battle_id
    return None


def run_spawn_hunt_test(
    caller,
    chart: SpawnChart,
    *,
    band: int,
    rng: Optional[random.Random] = None,
    battle_session_cls=BattleSession,
) -> SpawnHuntTestResult:
    if active_battle_for(caller, battle_session_cls=battle_session_cls):
        raise SpawnHuntTestError("You are already in a battle!")

    roll = roll_spawn(chart, band, rng=rng)
    session = battle_session_cls(caller)
    session.start_test_battle(
        species=roll.species_id,
        level=roll.level,
        opponent_kind="wild",
    )
    return SpawnHuntTestResult(roll=roll, battle_id=getattr(session, "battle_id", 0))

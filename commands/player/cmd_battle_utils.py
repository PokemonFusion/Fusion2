"""Utility helpers for battle-related commands.

This module centralizes imports and shared helpers used by the various
battle command modules.  Importing from here avoids repeated boilerplate
across the individual command files.
"""

from __future__ import annotations

NOT_IN_BATTLE_MSG = "You are not currently in battle."


def _get_participant(inst, caller):
    """Return battle participant for caller or fallback to first."""
    if inst and getattr(inst, "battle", None):
        for part in getattr(inst.battle, "participants", []):
            if getattr(part, "player", None) is caller:
                return part
        if getattr(inst.battle, "participants", []):
            return inst.battle.participants[0]
    return None


__all__ = ["NOT_IN_BATTLE_MSG", "_get_participant"]


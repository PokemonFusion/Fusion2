"""Utilities for managing simple character-level battle locks."""

from __future__ import annotations


def set_battle_lock(caller, battle_id: str) -> None:
    """Set a battle lock on ``caller`` with the given ``battle_id``.

    Parameters
    ----------
    caller
        The Character object to lock.
    battle_id
        Identifier for the battle this character is participating in.
    """
    caller.db.battle_lock = battle_id


def clear_battle_lock(caller) -> None:
    """Clear any active battle lock from ``caller``."""
    if hasattr(caller.db, "battle_lock"):
        del caller.db.battle_lock


def require_no_battle_lock(caller) -> bool:
    """Ensure ``caller`` is not currently in battle.

    Returns
    -------
    bool
        ``True`` if the caller is free to act, ``False`` otherwise. When the
        caller is in battle a message will be sent.
    """
    db = getattr(caller, "db", None)
    if db and getattr(db, "battle_lock", None):
        caller.msg("You cannot do that during battle.")
        return False

    ndb = getattr(caller, "ndb", None)
    if ndb and getattr(ndb, "battle_instance", None):
        caller.msg("You cannot do that during battle.")
        return False

    return True

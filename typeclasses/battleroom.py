"""Backward-compatible BattleRoom typeclass."""

from .rooms import BattleRoom as _BattleRoom


class BattleRoom(_BattleRoom):
    """Compatibility shim preserving legacy import path."""

    pass

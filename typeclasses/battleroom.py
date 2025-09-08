"""Backward-compatible BattleRoom typeclass.

This module simply re-exports :class:`typeclasses.rooms.BattleRoom` under the
legacy ``typeclasses.battleroom`` path. Importing :class:`BattleRoom` from this
module will therefore return the original implementation without creating a
duplicate Django model.
"""

from .rooms import BattleRoom

__all__ = ["BattleRoom"]

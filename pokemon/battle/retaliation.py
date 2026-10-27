"""Read qualifying retaliation hits from the actual move-damage ledger."""

from dataclasses import dataclass
from typing import Any

from .active_slots import active_at, slot_for


@dataclass(frozen=True)
class RetaliationHit:
    """A current opposing hit and the living occupant of its attacking slot."""

    source: Any
    target: Any
    damage: int
    category: str

    @classmethod
    def current(cls, pokemon, battle=None, *, category=None):
        """Reject missing, stale, allied, non-move and wrong-category damage."""
        temporary = getattr(pokemon, "tempvals", {}) or {}
        last = temporary.get("last_opposing_damage") or temporary.get("last_damaged_by")
        if not isinstance(last, dict) or not last.get("this_turn"):
            return None
        battle = battle or getattr(pokemon, "battle", None)
        if battle is None or last.get("turn", battle.turn_count) != battle.turn_count:
            return None
        source, move = last.get("source"), last.get("move")
        actual_category = getattr(move, "category", None) or (getattr(move, "raw", {}) or {}).get("category")
        if actual_category not in {"Physical", "Special"} or (category and actual_category != category):
            return None
        damage = last.get("damage", 0)
        if not isinstance(damage, (int, float)) or damage <= 0:
            return None
        owner, opposing = battle.participant_for(pokemon), battle.participant_for(source)
        if owner is None or opposing not in battle.opponents_of(owner):
            return None
        slot = last.get("source_slot")
        if slot is None:
            slot = slot_for(opposing, source)
        target = active_at(opposing, slot) if slot is not None else None
        if target is None or getattr(target, "hp", 0) <= 0:
            return None
        return cls(source, target, int(damage), actual_category)

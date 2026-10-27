"""Presentation names tied to battler identity and stable field positions."""

from __future__ import annotations

from .active_slots import active_slots


class BattlerLabels:
    """Disambiguate names in larger battles without changing Pokemon identity."""

    def __init__(self, battle):
        """Read positions from the current engine without keeping a stale roster."""
        self.battle = battle

    def position(self, pokemon):
        """Return the current physical position, including a Multi trainer's slot."""
        participants = getattr(self.battle, "participants", ())
        capacity = sum(getattr(part, "max_active", 1) for part in participants)
        if capacity <= 2:
            return None
        for index, part in enumerate(participants):
            slot = next((slot for slot, mon in active_slots(part, update=False).items()
                         if mon is pokemon), None)
            if slot is None:
                continue
            fixed = getattr(part, "field_position", None)
            if fixed:
                return fixed
            team = getattr(part, "team", None) or ("A" if index == 0 else "B")
            return f"{team}{slot + 1}"
        return None

    def name(self, pokemon, name=None):
        """Append a field label to a display name; reserves and singles stay plain."""
        if name is None:
            name = (getattr(pokemon, "name", None)
                    or getattr(pokemon, "nickname", None)
                    or getattr(pokemon, "species", None) or "Pokemon")
        position = self.position(pokemon)
        return f"{name} ({position})" if position else str(name)

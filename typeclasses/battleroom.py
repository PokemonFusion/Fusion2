"""Simple temporary room used for battles."""

from typeclasses.rooms import Room


class BattleRoom(Room):
    """A basic room for handling battles."""

    def at_object_creation(self):
        super().at_object_creation()
        # Mark as temporary; cleanup should remove this room after battle
        self.locks.add("view:all();delete:perm(Builders)")


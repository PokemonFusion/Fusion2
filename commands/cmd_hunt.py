"""Command for starting a temporary hunting instance."""
from __future__ import annotations

from evennia import Command, create_object

from fusion2.world.pokemon_spawn import get_spawn
from fusion2.typeclasses.rooms import Room


class CmdHunt(Command):
    """Start a temporary hunting room and spawn a wild Pokémon."""

    key = "+hunt"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def parse(self):
        self.args = self.args.strip()
        self.gen = None
        self.tier = None
        if not self.args:
            return
        for part in self.args.split():
            if part.lower().startswith("gen="):
                self.gen = part.split("=", 1)[1]
            elif part.lower().startswith("tier="):
                self.tier = part.split("=", 1)[1]

    def func(self):
        if self.caller.ndb.get("hunt_room"):
            self.caller.msg("You are already hunting.")
            return

        hunt_room = create_object(Room, key=f"Hunt-{self.caller.key}")
        self.caller.ndb.hunt_room = hunt_room
        self.caller.move_to(hunt_room, quiet=True)
        tiers = [self.tier] if self.tier else None
        gens = [self.gen] if self.gen else None
        spawn = get_spawn(self.caller.location, tiers=tiers, generations=gens)
        if spawn:
            self.caller.msg(f"A wild {spawn.species.name} (Lv{spawn.level}) appears!")
        else:
            self.caller.msg("Nothing seems to appear...")


class CmdLeaveHunt(Command):
    """Leave a hunting instance."""

    key = "+leave"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        room = self.caller.ndb.get("hunt_room")
        if not room:
            self.caller.msg("You are not hunting.")
            return
        self.caller.move_to(room.home or self.caller.home, quiet=True)
        room.delete()
        del self.caller.ndb.hunt_room
        self.caller.msg("You stop hunting.")

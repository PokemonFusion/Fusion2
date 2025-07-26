"""
Characters

Characters are (by default) Objects setup to be puppeted by Accounts.
They are what you "see" in game. The Character class in this module
is setup to be the "default" character type created by the default
creation commands.

"""

from evennia.objects.objects import DefaultCharacter

from .objects import ObjectParent
from utils.pokedex import DexTrackerMixin


class Character(DexTrackerMixin, ObjectParent, DefaultCharacter):
    """Default in-game character."""

    def at_init(self):
        super().at_init()
        bid = self.db.battle_id
        if bid is not None and not getattr(self.ndb, "battle_instance", None):
            room = self.location
            bmap = getattr(getattr(room, "ndb", None), "battle_instances", None)
            if isinstance(bmap, dict):
                inst = bmap.get(bid)
                if inst:
                    self.ndb.battle_instance = inst

    def at_post_puppet(self):
        super().at_post_puppet()
        bid = self.db.battle_id
        if bid is not None and not getattr(self.ndb, "battle_instance", None):
            room = self.location
            bmap = getattr(getattr(room, "ndb", None), "battle_instances", None)
            if isinstance(bmap, dict):
                inst = bmap.get(bid)
                if inst:
                    self.ndb.battle_instance = inst

    def at_pre_move(self, destination, **kwargs):
        """Prevent leaving while hosting a PVP request."""
        if getattr(self.db, "pvp_locked", False):
            self.msg("|rYou can't leave while waiting for a PVP battle.|n")
            return False
        return super().at_pre_move(destination, **kwargs)

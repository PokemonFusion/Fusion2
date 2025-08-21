"""
Characters

Characters are (by default) Objects setup to be puppeted by Accounts.
They are what you "see" in game. The Character class in this module
is setup to be the "default" character type created by the default
creation commands.

"""

import importlib.machinery
import importlib.util
import os
import sys

from evennia.objects.objects import DefaultCharacter

_BASE_PATH = os.path.dirname(__file__)
if "typeclasses" not in sys.modules:
    spec_pkg = importlib.machinery.ModuleSpec(
        "typeclasses", loader=None, is_package=True
    )
    pkg = importlib.util.module_from_spec(spec_pkg)
    pkg.__path__ = [_BASE_PATH]
    sys.modules["typeclasses"] = pkg

try:
    from .objects import ObjectParent
except Exception:  # pragma: no cover - fallback when package missing
    spec_obj = importlib.util.spec_from_file_location(
        "typeclasses.objects", os.path.join(_BASE_PATH, "objects.py")
    )
    mod_obj = importlib.util.module_from_spec(spec_obj)
    sys.modules[spec_obj.name] = mod_obj
    spec_obj.loader.exec_module(mod_obj)
    ObjectParent = mod_obj.ObjectParent  # type: ignore[attr-defined]

from django.utils.translation import gettext as _

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
        inst = getattr(self.ndb, "battle_instance", None)
        if inst:
            try:
                self.execute_cmd("+showbattle")
            except Exception:
                pass

    def at_pre_move(self, destination, **kwargs):
        """Prevent leaving while hosting a PVP request."""
        if getattr(self.db, "pvp_locked", False):
            self.msg("|rYou can't leave while waiting for a PVP battle.|n")
            return False
        return super().at_pre_move(destination, **kwargs)

    def at_say(
        self,
        message,
        msg_self=None,
        msg_location=None,
        receivers=None,
        msg_receivers=None,
        **kwargs,
    ):
        """Echo speech using the character's name to themselves.

        By default Evennia shows "You say" to the speaker while others see
        "<name> says".  This override aligns the speaker's view with everyone
        else's so that the player's name is shown in their own say messages as
        well.

        Args:
            message (str): The text to say.
            msg_self (str or bool, optional): Custom self message or a truthy
                value to use the default name-based format.
            msg_location (str, optional): Message for the location.
            receivers (DefaultObject or iterable, optional): Whom to whisper to.
            msg_receivers (str, optional): Message for specific receivers.
            **kwargs: Passed on to the parent implementation.
        """

        if (msg_self is None or msg_self is True) and not kwargs.get("whisper", False):
            msg_self = _('{object} says, "|n{speech}|n"')

        return super().at_say(
            message,
            msg_self=msg_self,
            msg_location=msg_location,
            receivers=receivers,
            msg_receivers=msg_receivers,
            **kwargs,
        )

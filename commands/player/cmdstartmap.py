from evennia import Command

from world import maphandler


def map_prototype_enabled() -> bool:
    """Return whether prototype map commands should be exposed."""

    try:
        from django.conf import settings
    except Exception:
        return False

    for name in ("DEV_MODE", "MAP_PROTOTYPE_ENABLED"):
        try:
            if bool(getattr(settings, name, False)):
                return True
        except Exception:
            continue
    return False


def require_map_prototype_access(caller) -> bool:
    if map_prototype_enabled():
        return True
    caller.msg("Map prototype commands are not available right now.")
    return False


class CmdStartMap(Command):
    """Start a map instance for solo adventuring.

    Usage:
      +map/start

    Examples:
      +map/start

    Notes:
      This creates a temporary solo map instance for your character.
    """

    key = "+map/start"
    aliases = ["@startmap"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        if not require_map_prototype_access(self.caller):
            return
        room = maphandler.create_map_instance(self.caller)
        self.caller.msg(f"Entering map instance: {room.key}")

"""
Exits

Exits are connectors between Rooms. An exit always has a destination property
set and has a single command defined on itself with the same name as its key,
for allowing Characters to traverse the exit to its destination.

"""

from evennia.objects.objects import DefaultExit

from utils.exit_display import format_exit_name

from .objects import ObjectParent


class Exit(ObjectParent, DefaultExit):
    """Exit connecting two rooms.

    Exits are normal :class:`evennia.objects.objects.DefaultObject` subclasses
    that define a ``destination`` and may customize traversal behavior.

    See ``mygame/typeclasses/objects.py`` for available properties and
    methods common to all object child classes.
    """

    # Exits should never override core command aliases such as ``look``. By
    # giving exits a lower priority than the default cmdset, regular commands
    # will take precedence when there is a name clash with an exit alias (for
    # example, an exit alias ``l`` will no longer shadow the ``look`` command).
    priority = -1

    appearance_template = """
{header}
{name}{extra_name_info}
{desc}
{exits}
{characters}
{things}
{footer}
    """

    def get_display_name(self, looker=None, **kwargs):
        """Display exit names with the same shortcut coloring used in room lists."""
        return format_exit_name(getattr(self, "key", ""))

    def get_extra_display_name_info(self, looker=None, **kwargs):
        """Add builder metadata and traversal flags without changing exit coloring."""
        parts = []
        if self._looker_is_builder(looker):
            ident = getattr(self, "id", None)
            parts.append(f"|y(#{ident})|n" if ident is not None else "|y(#?)|n")

        flags = []
        if looker and not self._can_traverse(looker):
            flags.append("|rLocked|n")
        if self._looker_is_builder(looker) and getattr(getattr(self, "db", None), "dark", False):
            flags.append("|mDark|n")
        if flags:
            parts.append(f"[{' '.join(flags)}]")

        return f" {' '.join(parts)}" if parts else ""

    def _can_traverse(self, looker) -> bool:
        """Return whether ``looker`` can traverse this exit."""
        try:
            return bool(self.access(looker, "traverse"))
        except Exception:
            return True

    def _looker_is_builder(self, looker) -> bool:
        """Return whether ``looker`` should see builder-only exit metadata."""
        if not looker:
            return False
        try:
            return bool(looker.check_permstring("Builder"))
        except Exception:
            pass
        locks = getattr(self, "locks", None)
        if locks and hasattr(locks, "check_lockstring"):
            try:
                return bool(locks.check_lockstring(looker, "perm(Builder)"))
            except Exception:
                return False
        return False

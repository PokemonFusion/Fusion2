"""
Exits

Exits connect Rooms and expose their names and aliases as traversal commands.

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

    # Core commands take precedence over a conflicting traversal name.
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

    def create_exit_cmdset(self, exidbobj):
        """Keep safe traversal names when another alias matches a core command.

        Evennia merges whole commands by overlapping names and aliases. Give
        each traversal name its own command so a conflict such as ``l`` with
        ``look`` removes only that shortcut, rather than the entire exit.
        """
        from evennia.commands.cmdset import CmdSet

        exit_cmdset = CmdSet(None)
        exit_cmdset.key = "ExitCmdSet"
        exit_cmdset.priority = self.priority
        exit_cmdset.duplicates = True
        names = [exidbobj.db_key, *exidbobj.aliases.all()]
        for name in dict.fromkeys(name.strip().lower() for name in names if name.strip()):
            exit_cmdset.add(
                self.exit_command(
                    key=name,
                    aliases=[],
                    locks=str(exidbobj.locks),
                    auto_help=False,
                    destination=exidbobj.db_destination,
                    arg_regex=r"^$",
                    is_exit=True,
                    obj=exidbobj,
                )
            )
        return exit_cmdset

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

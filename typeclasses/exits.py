"""
Exits

Exits are connectors between Rooms. An exit always has a destination property
set and has a single command defined on itself with the same name as its key,
for allowing Characters to traverse the exit to its destination.

"""

from evennia.objects.objects import DefaultExit

from .objects import ObjectParent


class Exit(ObjectParent, DefaultExit):
	"""
	Exits are connectors between rooms. Exits are normal Objects except
	they defines the `destination` property and overrides some hooks
	and methods to represent the exits.

	See mygame/typeclasses/objects.py for a list of
	properties and methods available on all Objects child classes like this.

	"""

        # Exits should never override core command aliases such as ``look``.
        # By giving exits a lower priority than the default cmdset, regular
        # commands will take precedence when there is a name clash with an
        # exit alias (for example, an exit alias ``l`` will no longer shadow
        # the ``look`` command).
        priority = -1

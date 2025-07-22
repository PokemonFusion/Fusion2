"""
Account

The Account represents the game "account" and each login has only one
Account object. An Account is what chats on default channels but has no
other in-game-world existence. Rather the Account puppets Objects (such
as Characters) in order to actually participate in the game world.


Guest

Guest accounts are simple low-level accounts that are created/deleted
on the fly and allows users to test the game without the commitment
of a full registration. Guest accounts are deactivated by default; to
activate them, add the following line to your settings file:

    GUEST_ENABLED = True

You will also need to modify the connection screen to reflect the
possibility to connect with a guest account. The setting file accepts
several more options for customizing the Guest account system.

"""

from evennia.accounts.accounts import DefaultAccount, DefaultGuest


class Account(DefaultAccount):
    """Game account typeclass with customized instructions."""

    #: When logging into an account, Evennia displays this template while the
    #: user is out-of-character.  The default text references the ``ic`` and
    #: ``ooc`` commands, which this game has renamed to ``goic`` and ``goooc``.
    #: Override the template here so the login screen remains accurate.
    ooc_appearance_template = (
        """
--------------------------------------------------------------------
{header}

{sessions}

  |whelp|n - more commands
  |wpublic <text>|n - talk on public channel
  |wcharcreate <name> [=description]|n - create new character
  |wchardelete <name>|n - delete a character
  |wgoic <name>|n - enter the game as character (|wgoooc|n to get back here)
  |wgoic|n - enter the game as latest character controlled.

{characters}
{footer}
--------------------------------------------------------------------
        """.strip()
    )

    def at_look(self, target=None, session=None, **kwargs):
        """Return the account's OOC appearance with custom commands."""
        text = super().at_look(target=target, session=session, **kwargs)
        return text.replace("|wic <name>|n", "|wgoic <name>|n")


class Guest(DefaultGuest):
    """
    This class is used for guest logins. Unlike Accounts, Guests and their
    characters are deleted after disconnection.
    """

    pass

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

from django.conf import settings
from django.utils.translation import gettext as _
from django.db import close_old_connections
from evennia.accounts.accounts import DefaultAccount, DefaultGuest
from evennia.utils.utils import is_iter

from utils.channel_identity import format_channel_message
from utils.character_mail import character_identity, unread_mail_counts_for_characters
from utils.site_status import get_login_block_message, is_login_blocked


class Account(DefaultAccount):
    """Game account typeclass with customized instructions."""

    #: When logging into an account, Evennia displays this template while the
    #: user is out-of-character.  The default text references the ``ic`` and
    #: ``ooc`` commands, which this game has renamed to ``goic`` and ``goooc``.
    #: Override the template here so the login screen remains accurate.
    ooc_appearance_template = """
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

    @classmethod
    def authenticate(cls, username, password, ip="", **kwargs):
        """Authenticate accounts while respecting the public play status."""

        close_old_connections()
        account, errors = super().authenticate(username, password, ip=ip, **kwargs)
        if account and is_login_blocked(account):
            return None, [_("|r%s|n") % get_login_block_message()]
        return account, errors

    def at_pre_login(self, **kwargs):
        """Hook retained for login lifecycle customization.

        Maintenance-mode rejection happens in ``authenticate`` so users receive
        a normal login error instead of an uncaught session-handler exception.
        """

        super().at_pre_login(**kwargs)

    def at_look(self, target=None, session=None, **kwargs):
        """Return the account's OOC appearance with numbered characters."""

        if target and not is_iter(target):
            text = super().at_look(target=target, session=session, **kwargs)
            return text.replace("|wic <name>|n", "|wgoic <name>|n")

        characters = [tar for tar in target if tar] if target else []
        # Preserve the order shown to the player for use by the ``goic`` command.
        self.ndb.character_selection_order = list(characters)

        sessions = list(self.sessions.all())
        if not sessions:
            # No active sessions connected to this account.
            return ""

        txt_header = f"Account |g{self.name}|n (you are Out-of-Character)"

        sess_strings = []
        for index, sess in enumerate(sessions, start=1):
            ip_addr = sess.address[0] if isinstance(sess.address, tuple) else sess.address
            addr = f"{sess.protocol_key} ({ip_addr})"
            if session and session.sessid == sess.sessid:
                prefix = f"|w* {index}|n"
            else:
                prefix = f"  {index}"
            sess_strings.append(f"{prefix} {addr}")
        txt_sessions = "|wConnected session(s):|n\n" + "\n".join(sess_strings)

        if not characters:
            txt_characters = "You don't have a character yet. Use |wcharcreate|n."
            mail_counts = {}
        else:
            max_chars = (
                "unlimited"
                if self.is_superuser or settings.MAX_NR_CHARACTERS is None
                else settings.MAX_NR_CHARACTERS
            )
            mail_counts = self._unread_mail_counts(characters)

            char_strings = []
            for index, char in enumerate(characters, start=1):
                prefix = f"  {index}. "
                permissions = ", ".join(char.permissions.all())
                connected_sessions = list(char.sessions.all())
                mail_notice = self._mail_notice(char, mail_counts)

                if connected_sessions:
                    statuses = []
                    controlled_by_account = False
                    for sess in connected_sessions:
                        session_index = sessions.index(sess) + 1 if sess in sessions else None
                        if session_index:
                            statuses.append(f"played by you in session {session_index}")
                            controlled_by_account = True
                        else:
                            statuses.append("played by someone else")

                    status_text = "; ".join(list(dict.fromkeys(statuses)))
                    name = f"|G{char.name}|n" if controlled_by_account else f"|R{char.name}|n"
                    char_strings.append(
                        f"{prefix}{name} [{permissions}] ({status_text}){mail_notice}"
                    )
                else:
                    char_strings.append(f"{prefix}{char.name} [{permissions}]{mail_notice}")

            txt_characters = (
                f"Available character(s) ({len(characters)}/{max_chars}, |wgoic <name>|n or |wgoic <#>|n to play):|n\n"
                + "\n".join(char_strings)
            )

        footer = self._mail_footer(characters, mail_counts)

        return self.ooc_appearance_template.format(
            header=txt_header,
            sessions=txt_sessions,
            characters=txt_characters,
            footer=footer,
        )

    def _unread_mail_counts(self, characters):
        """Return unread mail counts for the OOC character selector."""

        try:
            return unread_mail_counts_for_characters(characters)
        except Exception:
            return {}

    def _mail_notice(self, char, mail_counts):
        """Return a compact unread-mail notice for one character row."""

        count = mail_counts.get(character_identity(char), 0)
        return f" |y[{count} unread mail]|n" if count else ""

    def _mail_footer(self, characters, mail_counts):
        """Return the OOC unread-mail summary line."""

        if not mail_counts:
            return ""

        parts = []
        for char in characters:
            count = mail_counts.get(character_identity(char), 0)
            if count:
                parts.append(f"{char.name} ({count})")
        if not parts:
            return ""
        return "\n|yUnread mail:|n " + ", ".join(parts) + ". Use |wgoic|n, then |w+mail|n."

    def at_pre_channel_msg(self, message, channel, senders=None, **kwargs):
        """Display IC channel sends by character and OOC sends by marked account."""

        return format_channel_message(message, channel, senders=senders, receiver=self, **kwargs)


class Guest(DefaultGuest):
    """Guest account typeclass."""

    pass

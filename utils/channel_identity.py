"""Channel sender display helpers."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

ACCOUNT_CHANNEL_COLOR = "|m"
ACCOUNT_CHANNEL_MARKER = "(A)"


def format_channel_message(message: str, channel: Any, senders=None, receiver=None, **kwargs) -> str:
    """Format a channel message using PF2 account/character sender identity."""

    senders = _as_list(senders)
    if senders:
        sender_string = ", ".join(
            channel_sender_display_name(sender, receiver=receiver, **kwargs)
            for sender in senders
        )
        message_lstrip = message.lstrip()
        if message_lstrip.startswith((":", ";")):
            spacing = "" if message_lstrip[1:].startswith((":", "'", ",")) else " "
            message = f"{sender_string}{spacing}{message_lstrip[1:]}"
        else:
            message = f"{sender_string}: {message}"

    if not kwargs.get("no_prefix") and not kwargs.get("emit"):
        message = channel.channel_prefix() + message

    return message


def channel_sender_display_name(sender: Any, receiver=None, sender_session=None, **kwargs) -> str:
    """Return the display name to use for a channel sender."""

    puppet = active_sender_puppet(sender, sender_session=sender_session)
    if puppet:
        return _display_name(puppet, receiver)
    if _looks_like_account(sender):
        return account_channel_display_name(sender, receiver=receiver)
    return _display_name(sender, receiver)


def account_channel_display_name(account: Any, receiver=None) -> str:
    """Return the marked account display name for OOC/account channel sends."""

    name = _display_name(account, receiver)
    return f"{ACCOUNT_CHANNEL_COLOR}{ACCOUNT_CHANNEL_MARKER} {name}|n"


def active_sender_puppet(sender: Any, sender_session=None):
    """Find the character puppet associated with this channel send, if any."""

    if sender_session:
        puppet = _session_puppet(sender_session)
        if _puppet_belongs_to_sender(puppet, sender):
            return puppet

    get_all_puppets = getattr(sender, "get_all_puppets", None)
    if callable(get_all_puppets):
        try:
            puppets = [puppet for puppet in get_all_puppets() if puppet]
        except Exception:
            puppets = []
        if len(puppets) == 1:
            return puppets[0]

    puppet = getattr(sender, "puppet", None)
    if isinstance(puppet, Iterable) and not isinstance(puppet, (str, bytes)):
        puppets = [candidate for candidate in puppet if candidate]
        return puppets[0] if len(puppets) == 1 else None
    return puppet or None


def _session_puppet(session):
    get_puppet = getattr(session, "get_puppet", None)
    if callable(get_puppet):
        puppet = get_puppet()
        if puppet:
            return puppet
    return getattr(session, "puppet", None)


def _puppet_belongs_to_sender(puppet, sender) -> bool:
    if not puppet:
        return False
    account = getattr(puppet, "account", None)
    return account in (None, sender)


def _looks_like_account(sender) -> bool:
    if getattr(sender, "is_account", False):
        return True
    typeclass_path = str(getattr(sender, "typeclass_path", ""))
    if typeclass_path.endswith("accounts.Account"):
        return True
    return callable(getattr(sender, "get_puppet", None)) and hasattr(sender, "characters")


def _display_name(obj, receiver=None) -> str:
    get_display_name = getattr(obj, "get_display_name", None)
    if callable(get_display_name):
        try:
            return get_display_name(receiver)
        except TypeError:
            return get_display_name()
    return str(getattr(obj, "key", None) or getattr(obj, "name", obj))


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return list(value)
    return [value]

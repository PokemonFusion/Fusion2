"""Character-scoped in-game mail helpers."""

from __future__ import annotations


MAIL_TAG = "character_mail"
MAIL_CATEGORY = "pf2_mail"
UNREAD_TAG = "unread"
MAX_MAIL_SUBJECT_LENGTH = 80
MAX_MAIL_BODY_LENGTH = 4000


class CharacterMailError(ValueError):
    """Raised when a character mail operation cannot be completed."""


def _msg_model():
    """Return Evennia's Msg model lazily for testability."""

    from evennia.comms.models import Msg

    return Msg


def _create_message(sender, body: str, recipient, subject: str):
    """Create a persistent Evennia message tagged as PF2 character mail."""

    from evennia.utils import create

    return create.create_message(
        sender,
        body,
        receivers=recipient,
        header=subject,
        tags=[(MAIL_TAG, MAIL_CATEGORY), (UNREAD_TAG, MAIL_CATEGORY)],
    )


def character_identity(character):
    """Return a stable identity key for a character-like object."""

    return (
        getattr(character, "id", None)
        or getattr(character, "pk", None)
        or getattr(character, "dbref", None)
        or getattr(character, "key", None)
        or id(character)
    )


def character_name(character) -> str:
    """Return a display name for a character-like object."""

    return getattr(character, "key", None) or getattr(character, "name", None) or str(character)


def clean_subject(subject: str) -> str:
    """Normalize a mail subject."""

    cleaned = " ".join(str(subject or "").split())
    if len(cleaned) > MAX_MAIL_SUBJECT_LENGTH:
        cleaned = cleaned[:MAX_MAIL_SUBJECT_LENGTH].rstrip()
    return cleaned


def clean_body(body: str) -> str:
    """Normalize a mail body while preserving intentional line breaks."""

    cleaned = str(body or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if len(cleaned) > MAX_MAIL_BODY_LENGTH:
        cleaned = cleaned[:MAX_MAIL_BODY_LENGTH].rstrip()
    return cleaned


def _has_tag(message, tag: str) -> bool:
    tags = getattr(message, "tags", None)
    has = getattr(tags, "has", None)
    if callable(has):
        return bool(has(tag, category=MAIL_CATEGORY))
    get = getattr(tags, "get", None)
    if callable(get):
        return bool(get(tag, category=MAIL_CATEGORY))
    return bool(getattr(message, tag, False))


def _add_tag(message, tag: str) -> None:
    tags = getattr(message, "tags", None)
    add = getattr(tags, "add", None)
    if callable(add):
        add(tag, category=MAIL_CATEGORY)
    elif tag == UNREAD_TAG:
        setattr(message, "unread", True)


def _remove_tag(message, tag: str) -> None:
    tags = getattr(message, "tags", None)
    remove = getattr(tags, "remove", None)
    if callable(remove):
        remove(tag, category=MAIL_CATEGORY)
    elif tag == UNREAD_TAG:
        setattr(message, "unread", False)


def _mail_queryset(character):
    messages = _msg_model().objects.get_messages_by_receiver(character)
    if hasattr(messages, "filter"):
        messages = messages.filter(db_tags__db_key=MAIL_TAG, db_tags__db_category=MAIL_CATEGORY)
    else:
        messages = [message for message in messages if _has_tag(message, MAIL_TAG)]
    if hasattr(messages, "distinct"):
        messages = messages.distinct()
    if hasattr(messages, "order_by"):
        messages = messages.order_by("-db_date_created")
    else:
        messages = sorted(messages, key=lambda message: mail_date(message), reverse=True)
    return messages


def list_character_mail(character) -> list:
    """Return visible PF2 mail messages for ``character``, newest first."""

    return list(_mail_queryset(character))


def mail_id(message) -> int:
    """Return the stable database id for a mail message."""

    return int(getattr(message, "id", getattr(message, "pk", 0)))


def parse_mail_id(raw_id) -> int:
    """Normalize a user-provided mail id."""

    try:
        return int(str(raw_id).strip().lstrip("#"))
    except (TypeError, ValueError):
        raise CharacterMailError("Mail id must be a number.")


def get_character_mail(character, raw_id):
    """Return one visible mail message for a character."""

    needle = parse_mail_id(raw_id)
    for message in list_character_mail(character):
        if mail_id(message) == needle:
            return message
    raise CharacterMailError(f"No mail #{needle} found.")


def mail_subject(message) -> str:
    """Return a message subject."""

    return str(getattr(message, "header", None) or getattr(message, "db_header", "") or "(No subject)")


def mail_body(message) -> str:
    """Return a message body."""

    return str(getattr(message, "message", None) or getattr(message, "db_message", "") or "")


def mail_date(message):
    """Return the created date for a message."""

    return getattr(message, "date_created", None) or getattr(message, "db_date_created", "")


def mail_senders(message) -> list:
    """Return message senders as a list."""

    senders = getattr(message, "senders", [])
    return list(senders or [])


def sender_name(message) -> str:
    """Return a display name for the first sender."""

    senders = mail_senders(message)
    return character_name(senders[0]) if senders else "Unknown"


def is_unread(message) -> bool:
    """Return whether a mail message is unread."""

    return _has_tag(message, UNREAD_TAG)


def mark_read(message):
    """Mark a mail message read."""

    _remove_tag(message, UNREAD_TAG)
    return message


def mark_unread(message):
    """Mark a mail message unread."""

    _add_tag(message, UNREAD_TAG)
    return message


def send_character_mail(sender, recipient, subject: str, body: str):
    """Send one character-scoped mail message."""

    clean_subj = clean_subject(subject)
    clean_msg = clean_body(body)
    if not clean_subj:
        raise CharacterMailError("Mail subject cannot be empty.")
    if not clean_msg:
        raise CharacterMailError("Mail message cannot be empty.")

    message = _create_message(sender, clean_msg, recipient, clean_subj)
    if not message:
        raise CharacterMailError("Mail could not be sent.")

    notify = getattr(recipient, "msg", None)
    if callable(notify):
        notify(f"You have new mail from {character_name(sender)}: {clean_subj}")
    return message


def read_character_mail(character, raw_id):
    """Return a visible mail message and mark it read."""

    message = get_character_mail(character, raw_id)
    mark_read(message)
    return message


def reply_to_character_mail(character, raw_id, body: str):
    """Reply to the first sender of a visible mail message."""

    original = read_character_mail(character, raw_id)
    senders = mail_senders(original)
    if not senders:
        raise CharacterMailError("That mail has no sender to reply to.")
    subject = mail_subject(original)
    if not subject.lower().startswith("re:"):
        subject = f"RE: {subject}"
    return send_character_mail(character, senders[0], subject, body)


def archive_character_mail(character, raw_id):
    """Hide a mail message from one character's inbox."""

    message = get_character_mail(character, raw_id)
    hidden = getattr(message, "db_hide_from_objects", None)
    add = getattr(hidden, "add", None)
    if callable(add):
        add(character)
    else:
        hidden_for = getattr(message, "hidden_for", set())
        hidden_for.add(character_identity(character))
        setattr(message, "hidden_for", hidden_for)
    mark_read(message)
    return message


def unread_mail_count(character) -> int:
    """Return the number of unread mail messages for a character."""

    return sum(1 for message in list_character_mail(character) if is_unread(message))


def unread_mail_counts_for_characters(characters) -> dict:
    """Return unread mail counts keyed by character identity."""

    counts = {}
    for character in characters:
        count = unread_mail_count(character)
        if count:
            counts[character_identity(character)] = count
    return counts

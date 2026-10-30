import types

import pytest

from utils import character_mail


class FakeTags:
    def __init__(self, tags=()):
        self.tags = set(tags)

    def add(self, key, category=None):
        self.tags.add((key, category))

    def remove(self, key, category=None):
        self.tags.discard((key, category))

    def has(self, key, category=None):
        return (key, category) in self.tags


class FakeMessage:
    def __init__(self, ident, sender, recipient, subject, body, date):
        self.id = ident
        self.senders = [sender]
        self.receivers = [recipient]
        self.header = subject
        self.message = body
        self.date_created = date
        self.tags = FakeTags(
            (
                (character_mail.MAIL_TAG, character_mail.MAIL_CATEGORY),
                (character_mail.UNREAD_TAG, character_mail.MAIL_CATEGORY),
            )
        )
        self.hidden_for = set()


class FakeQuerySet(list):
    def filter(self, db_tags__db_key=None, db_tags__db_category=None):
        return FakeQuerySet(
            message
            for message in self
            if message.tags.has(db_tags__db_key, category=db_tags__db_category)
        )

    def distinct(self):
        return self

    def order_by(self, field):
        reverse = field.startswith("-")
        attr = field.lstrip("-")
        if attr == "db_date_created":
            attr = "date_created"
        return FakeQuerySet(sorted(self, key=lambda message: getattr(message, attr), reverse=reverse))


class FakeManager:
    def __init__(self):
        self.messages = []

    def get_messages_by_receiver(self, character):
        ident = character_mail.character_identity(character)
        return FakeQuerySet(
            message
            for message in self.messages
            if any(character_mail.character_identity(receiver) == ident for receiver in message.receivers)
            and ident not in message.hidden_for
        )


class FakeCharacter:
    def __init__(self, key, ident):
        self.key = key
        self.id = ident
        self.messages = []

    def msg(self, text):
        self.messages.append(text)


@pytest.fixture
def fake_mail_store(monkeypatch):
    manager = FakeManager()
    counter = {"id": 0}

    def create_message(sender, body, recipient, subject):
        counter["id"] += 1
        message = FakeMessage(counter["id"], sender, recipient, subject, body, counter["id"])
        manager.messages.append(message)
        return message

    monkeypatch.setattr(character_mail, "_msg_model", lambda: types.SimpleNamespace(objects=manager))
    monkeypatch.setattr(character_mail, "_create_message", create_message)
    return manager


def test_send_character_mail_stores_unread_message(fake_mail_store):
    sender = FakeCharacter("Ash", 1)
    recipient = FakeCharacter("Misty", 2)

    message = character_mail.send_character_mail(sender, recipient, "Hello", "Meet at the lab.")

    assert character_mail.mail_id(message) == 1
    assert character_mail.is_unread(message) is True
    assert character_mail.list_character_mail(recipient) == [message]
    assert recipient.messages == ["You have new mail from Ash: Hello"]


def test_read_mail_marks_message_read(fake_mail_store):
    sender = FakeCharacter("Ash", 1)
    recipient = FakeCharacter("Misty", 2)
    message = character_mail.send_character_mail(sender, recipient, "Hello", "Meet at the lab.")

    read = character_mail.read_character_mail(recipient, message.id)

    assert read is message
    assert character_mail.is_unread(message) is False


def test_reply_sends_to_original_sender_and_marks_original_read(fake_mail_store):
    sender = FakeCharacter("Ash", 1)
    recipient = FakeCharacter("Misty", 2)
    original = character_mail.send_character_mail(sender, recipient, "Plan", "Route 1?")

    reply = character_mail.reply_to_character_mail(recipient, original.id, "Yes.")

    assert character_mail.mail_subject(reply) == "RE: Plan"
    assert reply.receivers == [sender]
    assert character_mail.is_unread(original) is False
    assert sender.messages == ["You have new mail from Misty: RE: Plan"]


def test_archive_hides_message_from_inbox(fake_mail_store):
    sender = FakeCharacter("Ash", 1)
    recipient = FakeCharacter("Misty", 2)
    message = character_mail.send_character_mail(sender, recipient, "Hello", "Meet at the lab.")

    character_mail.archive_character_mail(recipient, message.id)

    assert character_mail.list_character_mail(recipient) == []


def test_unread_counts_are_keyed_by_character_identity(fake_mail_store):
    sender = FakeCharacter("Ash", 1)
    first = FakeCharacter("Misty", 2)
    second = FakeCharacter("Brock", 3)
    character_mail.send_character_mail(sender, first, "One", "Message")
    read = character_mail.send_character_mail(sender, first, "Two", "Message")
    character_mail.read_character_mail(first, read.id)
    character_mail.send_character_mail(sender, second, "Three", "Message")

    assert character_mail.unread_mail_counts_for_characters([first, second]) == {2: 1, 3: 1}

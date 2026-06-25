from types import SimpleNamespace

from utils.channel_identity import (
    account_channel_display_name,
    active_sender_puppet,
    format_channel_message,
)


class FakeChannel:
    def channel_prefix(self):
        return "[Public] "


class FakeAccount:
    is_account = True

    def __init__(self, key, puppets=None):
        self.key = key
        self.puppet = puppets or []

    def get_display_name(self, receiver=None):
        return self.key


class FakeCharacter:
    def __init__(self, key, account=None):
        self.key = key
        self.account = account

    def get_display_name(self, receiver=None):
        return self.key


class FakeSession:
    def __init__(self, puppet=None):
        self.puppet = puppet

    def get_puppet(self):
        return self.puppet


def test_ooc_account_sender_is_marked_and_colored():
    account = FakeAccount("Yang")

    output = format_channel_message("hello", FakeChannel(), senders=[account])

    assert output == "[Public] |m(A) Yang|n: hello"


def test_ic_account_sender_uses_session_puppet_name():
    account = FakeAccount("Yang")
    character = FakeCharacter("Pikaya", account=account)
    session = FakeSession(character)

    output = format_channel_message(
        "hello",
        FakeChannel(),
        senders=[account],
        sender_session=session,
    )

    assert output == "[Public] Pikaya: hello"


def test_sender_session_selects_character_when_account_has_multiple_puppets():
    account = FakeAccount("Yang")
    first = FakeCharacter("Pikaya", account=account)
    second = FakeCharacter("Raika", account=account)
    account.puppet = [first, second]

    assert active_sender_puppet(account, sender_session=FakeSession(second)) is second
    assert active_sender_puppet(account) is None


def test_ooc_pose_keeps_account_marker():
    account = FakeAccount("Yang")

    output = format_channel_message(":waves.", FakeChannel(), senders=[account])

    assert output == "[Public] |m(A) Yang|n waves."


def test_unmarked_object_senders_keep_plain_display_names():
    npc = SimpleNamespace(key="Guide")

    output = format_channel_message("welcome", FakeChannel(), senders=[npc])

    assert output == "[Public] Guide: welcome"


def test_account_marker_helper_uses_display_name():
    account = FakeAccount("Yang")

    assert account_channel_display_name(account) == "|m(A) Yang|n"

import types

import pytest

import utils.support_requests as support_requests


class FakeConfigObjects:
    def __init__(self):
        self.values = {}

    def conf(self, key, value=None, default=None, delete=False):
        if delete:
            self.values.pop(key, None)
            return None
        if value is not None:
            self.values[key] = value
            return value
        return self.values.get(key, default)


class FakeServerConfig:
    objects = FakeConfigObjects()


class FakePermissions:
    def __init__(self, perms=()):
        self.perms = list(perms)

    def all(self):
        return list(self.perms)


class FakeAccount:
    def __init__(self, key, ident, perms=()):
        self.key = key
        self.id = ident
        self.permissions = FakePermissions(perms)
        self.db = types.SimpleNamespace()


class FakeLocation:
    key = "Lobby"


class FakeCharacter:
    def __init__(self, key="Tester"):
        self.key = key
        self.id = 99
        self.location = FakeLocation()


@pytest.fixture(autouse=True)
def fake_config(monkeypatch):
    FakeServerConfig.objects = FakeConfigObjects()
    monkeypatch.setattr(support_requests, "_server_config", lambda: FakeServerConfig)


def test_create_request_records_account_character_and_location():
    account = FakeAccount("Player", 1)
    character = FakeCharacter()

    request = support_requests.create_request(account, character, "  I need help   with a stuck room.  ")

    assert request["id"] == 1
    assert request["status"] == "open"
    assert request["requester_account"] == "Player"
    assert request["requester_character"] == "Tester"
    assert request["location"] == "Lobby"
    assert request["text"] == "I need help with a stuck room."


def test_list_requests_can_filter_by_requester():
    player = FakeAccount("Player", 1)
    other = FakeAccount("Other", 2)
    support_requests.create_request(player, None, "first")
    support_requests.create_request(other, None, "second")

    rows = support_requests.list_requests(requester=player)

    assert [row["text"] for row in rows] == ["first"]


def test_staff_can_claim_and_close_request():
    player = FakeAccount("Player", 1)
    staff = FakeAccount("Staff", 2, perms=("Helper",))
    support_requests.create_request(player, None, "Need validation help.")

    claimed = support_requests.claim_request(1, staff)
    closed = support_requests.close_request(1, staff, note="Handled.")

    assert claimed["claimed_by"] == "Staff"
    assert closed["status"] == "closed"
    assert closed["closed_by"] == "Staff"
    assert closed["close_note"] == "Handled."


def test_players_can_only_close_their_own_requests():
    player = FakeAccount("Player", 1)
    other = FakeAccount("Other", 2)
    support_requests.create_request(player, None, "Need help.")

    with pytest.raises(support_requests.SupportRequestError, match="own support requests"):
        support_requests.close_request(1, other)

    closed = support_requests.close_request(1, player)
    assert closed["status"] == "closed"

import datetime as dt
import os
import types

import django
import pytest
from django.core.exceptions import PermissionDenied
from django.template.loader import render_to_string
from django.test import RequestFactory

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from web.admin import views
from web.admin.access import has_account_roster_access


class DummyPermissions:
    def __init__(self, permissions=()):
        self._permissions = set(permissions)

    def all(self):
        return sorted(self._permissions)

    def check(self, permission):
        return permission in self._permissions


class DummyUser:
    def __init__(self, *, authenticated=True, superuser=False, permissions=()):
        self.is_authenticated = authenticated
        self.is_superuser = superuser
        self.is_staff = False
        self.username = "Staff"
        self.permissions = DummyPermissions(permissions)

    def check_permstring(self, permission):
        return self.permissions.check(permission)


class DummyCharacters:
    def __init__(self, characters):
        self._characters = characters

    def all(self):
        return list(self._characters)


class DummySessions:
    def __init__(self, sessions=()):
        self._sessions = sessions

    def all(self):
        return list(self._sessions)


class DummyCharacter:
    def __init__(self, key, ident, *, location=None, online=False):
        self.key = key
        self.id = ident
        self.dbref = f"#{ident}"
        self.typeclass_path = "typeclasses.characters.Character"
        self.location = location
        self.sessions = DummySessions([object()] if online else [])


class DummyAccount:
    def __init__(self, username, ident, characters=(), *, permissions=(), superuser=False):
        self.username = username
        self.key = username
        self.id = ident
        self.dbref = f"#{ident}"
        self.characters = DummyCharacters(characters)
        self.permissions = DummyPermissions(permissions)
        self.is_superuser = superuser
        self.date_joined = dt.datetime(2026, 6, 1, 13, 30)
        self.last_login = None


class AccountQuery(list):
    def order_by(self, attr):
        return AccountQuery(sorted(self, key=lambda account: getattr(account, attr)))


class AccountManager:
    def __init__(self, accounts):
        self.accounts = AccountQuery(accounts)

    def all(self):
        return self.accounts


def test_account_roster_access_is_limited_to_admins_and_wizards():
    assert has_account_roster_access(DummyUser(superuser=True)) is True
    assert has_account_roster_access(DummyUser(permissions={"Admin"})) is True
    assert has_account_roster_access(DummyUser(permissions={"Wizards"})) is True
    assert has_account_roster_access(DummyUser(permissions={"Builder"})) is False
    assert has_account_roster_access(DummyUser(authenticated=False, permissions={"Admin"})) is False


def test_build_account_roster_lists_playable_characters():
    lab = types.SimpleNamespace(key="Alpha Lab")
    misty = DummyCharacter("Misty", 101, location=lab, online=True)
    brock = DummyCharacter("Brock", 102)
    account = DummyAccount("Trainer", 1, [misty, brock], permissions={"Player"})

    rows = views.build_account_roster([account])

    assert rows == [
        {
            "name": "Trainer",
            "dbref": "#1",
            "roles": ["Player"],
            "created": "2026-06-01 13:30",
            "last_login": "",
            "characters": [
                {
                    "name": "Misty",
                    "dbref": "#101",
                    "location": "Alpha Lab",
                    "typeclass": "Character",
                    "online": True,
                },
                {
                    "name": "Brock",
                    "dbref": "#102",
                    "location": "",
                    "typeclass": "Character",
                    "online": False,
                },
            ],
            "character_count": 2,
        }
    ]


def test_filter_account_roster_matches_character_fields():
    rows = views.build_account_roster(
        [
            DummyAccount("Trainer", 1, [DummyCharacter("Misty", 101)]),
            DummyAccount("Rival", 2, [DummyCharacter("Gary", 102)]),
        ]
    )

    filtered = views.filter_account_roster(rows, "misty")

    assert [row["name"] for row in filtered] == ["Trainer"]


def test_player_roster_view_rejects_non_admin_user():
    request = RequestFactory().get("/admin/player-roster/")
    request.user = DummyUser(permissions={"Builder"})

    with pytest.raises(PermissionDenied):
        views.player_roster(request)


def test_player_roster_view_builds_context_from_accountdb(monkeypatch):
    account = DummyAccount("Trainer", 1, [DummyCharacter("Misty", 101)])
    fake_accountdb = types.SimpleNamespace(objects=AccountManager([account]))
    captured = {}

    def fake_render(request, template, context):
        captured["template"] = template
        captured["context"] = context
        return types.SimpleNamespace(status_code=200)

    monkeypatch.setattr(views, "AccountDB", fake_accountdb)
    monkeypatch.setattr(views, "render", fake_render)

    request = RequestFactory().get("/admin/player-roster/?q=misty")
    request.user = DummyUser(permissions={"Admin"})

    response = views.player_roster(request)

    assert response.status_code == 200
    assert captured["template"] == "admin/player_roster.html"
    assert captured["context"]["query"] == "misty"
    assert captured["context"]["account_count"] == 1
    assert captured["context"]["displayed_account_count"] == 1
    assert captured["context"]["rows"][0]["characters"][0]["name"] == "Misty"


def test_player_roster_template_renders_with_nav_link():
    request = RequestFactory().get("/admin/player-roster/")
    request.user = DummyUser(permissions={"Admin"})
    request.session = {}

    html = render_to_string(
        "admin/player_roster.html",
        {
            "page_title": "Player Account Roster",
            "query": "",
            "rows": [
                {
                    "name": "Trainer",
                    "dbref": "#1",
                    "roles": ["Player"],
                    "created": "2026-06-01 13:30",
                    "last_login": "",
                    "characters": [
                        {
                            "name": "Misty",
                            "dbref": "#101",
                            "location": "Alpha Lab",
                            "typeclass": "Character",
                            "online": True,
                        }
                    ],
                    "character_count": 1,
                }
            ],
            "account_count": 1,
            "character_count": 1,
            "displayed_account_count": 1,
            "displayed_character_count": 1,
        },
        request=request,
    )

    assert "Player Account Roster" in html
    assert "Misty" in html
    assert "Player Roster" in html

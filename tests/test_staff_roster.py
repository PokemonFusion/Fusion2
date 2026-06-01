import types

from utils.staff_roster import (
    build_staff_rows,
    clear_staff_note,
    is_staff_account,
    set_staff_duty,
    set_staff_note,
    staff_roles_for_account,
)


class FakePermissions:
    def __init__(self, perms):
        self.perms = list(perms)

    def all(self):
        return list(self.perms)


class FakeAccount:
    def __init__(self, key, ident, perms=(), superuser=False):
        self.key = key
        self.id = ident
        self.is_superuser = superuser
        self.permissions = FakePermissions(perms)
        self.db = types.SimpleNamespace()


class FakeSession:
    def __init__(self, account):
        self.account = account

    def get_account(self):
        return self.account


def test_staff_roles_use_account_permissions_not_characters():
    helper = FakeAccount("Helper", 1, perms=("Helper",))
    player = FakeAccount("Player", 2, perms=("Player",))
    wizard = FakeAccount("Root", 3, superuser=True)

    assert staff_roles_for_account(helper) == ["Helper"]
    assert staff_roles_for_account(wizard) == ["Wizards"]
    assert is_staff_account(helper) is True
    assert is_staff_account(player) is False


def test_build_staff_rows_includes_offline_staff_and_online_status():
    admin = FakeAccount("Admin", 1, perms=("Admin",))
    validator = FakeAccount("Validator", 2, perms=("Validator",))
    player = FakeAccount("Player", 3, perms=("Player",))
    set_staff_note(admin, "Reviewing apps")
    set_staff_duty(validator, False)

    rows = build_staff_rows([validator, player, admin], [FakeSession(admin)])

    assert rows == [
        {
            "account": admin,
            "name": "Admin",
            "roles": ["Admin"],
            "status": "Online",
            "online": True,
            "note": "Reviewing apps",
        },
        {
            "account": validator,
            "name": "Validator",
            "roles": ["Validator"],
            "status": "Off duty",
            "online": False,
            "note": "",
        },
    ]


def test_staff_note_can_be_cleared():
    admin = FakeAccount("Admin", 1, perms=("Admin",))

    set_staff_note(admin, "A" * 200)
    assert len(admin.db.staff_note) == 80

    clear_staff_note(admin)
    assert admin.db.staff_note == ""

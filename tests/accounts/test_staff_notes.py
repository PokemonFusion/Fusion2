import types

import pytest

from utils.staff_notes import (
    StaffNoteError,
    add_staff_note,
    delete_staff_note,
    get_staff_note,
    list_staff_notes,
)


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


class FakeTarget:
    def __init__(self, key="Target"):
        self.key = key
        self.db = types.SimpleNamespace()


def test_staff_note_adds_normalized_note_to_target():
    staff = FakeAccount("Helper", 1, perms=("Helper",))
    target = FakeTarget()

    note = add_staff_note(target, staff, "  Validate after   profile update.  ")

    assert note["id"] == 1
    assert note["author"] == "Helper"
    assert list_staff_notes(target)[0]["text"] == "Validate after profile update."


def test_staff_notes_require_staff_author():
    player = FakeAccount("Player", 1, perms=("Player",))
    target = FakeTarget()

    with pytest.raises(StaffNoteError, match="Only staff"):
        add_staff_note(target, player, "Should fail.")


def test_staff_notes_can_be_read_and_deleted_by_id():
    staff = FakeAccount("Validator", 1, perms=("Validator",))
    target = FakeTarget()
    first = add_staff_note(target, staff, "First note.")
    second = add_staff_note(target, staff, "Second note.")

    assert get_staff_note(target, first["id"])["text"] == "First note."

    removed = delete_staff_note(target, second["id"])

    assert removed["text"] == "Second note."
    assert [note["id"] for note in list_staff_notes(target)] == [1]

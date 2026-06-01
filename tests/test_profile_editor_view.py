import os
import types

import django
import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from web.website.views.profile_editor import (
    ProfileError,
    apply_profile_editor_action,
    profile_character_choices,
    profile_field_rows,
    select_profile_character,
)


class DummyCharacters:
    def __init__(self, characters):
        self.characters = characters

    def all(self):
        return list(self.characters)


class DummyAccount:
    def __init__(self, characters):
        self.characters = DummyCharacters(characters)


class DummyChar:
    def __init__(self, key, ident):
        self.key = key
        self.id = ident
        self.db = types.SimpleNamespace()


def test_select_profile_character_stays_with_account_characters():
    ash = DummyChar("Ash", 1)
    misty = DummyChar("Misty", 2)
    account = DummyAccount([ash, misty])

    assert select_profile_character(account, "2") is misty
    assert select_profile_character(account, "999") is ash


def test_profile_character_choices_mark_selected_character():
    ash = DummyChar("Ash", 1)
    misty = DummyChar("Misty", 2)
    account = DummyAccount([ash, misty])

    choices = profile_character_choices(account, misty)

    assert choices == [
        {"id": 1, "name": "Ash", "selected": False},
        {"id": 2, "name": "Misty", "selected": True},
    ]


def test_apply_profile_editor_action_saves_and_deletes_fields():
    ash = DummyChar("Ash", 1)

    message = apply_profile_editor_action(
        ash,
        {"action": "save", "field_name": "Appearance", "field_text": "Red jacket.", "private": "1"},
    )
    rows = profile_field_rows(ash)

    assert message == "Profile field 'Appearance' saved."
    assert rows == [{"key": "appearance", "label": "Appearance", "text": "Red jacket.", "private": True}]

    message = apply_profile_editor_action(ash, {"action": "delete", "field_key": "appearance"})

    assert message == "Profile field deleted."
    assert profile_field_rows(ash) == []


def test_apply_profile_editor_action_rejects_unknown_action():
    ash = DummyChar("Ash", 1)

    with pytest.raises(ProfileError):
        apply_profile_editor_action(ash, {"action": "publish"})

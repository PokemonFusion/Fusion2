import types

import pytest

from utils.character_profiles import (
    ProfileError,
    delete_profile_field,
    field_key,
    get_profile_fields,
    set_profile_field,
    set_profile_field_privacy,
    visible_profile_fields,
)


class DummyChar:
    def __init__(self, key="Ash", ident=1, perms=None):
        self.key = key
        self.id = ident
        self.db = types.SimpleNamespace()
        self.perms = set(perms or [])

    def check_permstring(self, perm):
        return perm in self.perms


def test_profile_field_key_normalizes_labels():
    assert field_key("  Favorite Color! ") == "favorite-color"
    assert field_key("RP_Name") == "rp_name"


def test_set_update_and_delete_profile_field():
    char = DummyChar()

    field = set_profile_field(char, "Appearance", "Red jacket.", private=False)
    assert field == {"label": "Appearance", "text": "Red jacket.", "private": False}
    assert list(get_profile_fields(char)) == ["appearance"]

    set_profile_field(char, "Appearance", "Blue jacket.", private=True)
    fields = get_profile_fields(char)
    assert fields["appearance"]["text"] == "Blue jacket."
    assert fields["appearance"]["private"] is True

    assert delete_profile_field(char, "Appearance") is True
    assert get_profile_fields(char) == {}


def test_profile_rejects_empty_field_names_and_text():
    char = DummyChar()

    with pytest.raises(ProfileError):
        set_profile_field(char, "!!!", "Text")

    with pytest.raises(ProfileError):
        set_profile_field(char, "Title", "   ")


def test_private_fields_visible_to_owner_and_staff_only():
    owner = DummyChar("Owner", ident=1)
    viewer = DummyChar("Viewer", ident=2)
    validator = DummyChar("Validator", ident=3, perms={"Validator"})
    set_profile_field(owner, "Secret", "Hidden note.", private=True)
    set_profile_field(owner, "Public", "Visible note.", private=False)

    assert list(visible_profile_fields(owner, viewer)) == ["public"]
    assert set(visible_profile_fields(owner, owner)) == {"secret", "public"}
    assert set(visible_profile_fields(owner, validator)) == {"secret", "public"}


def test_privacy_toggle_requires_existing_field():
    char = DummyChar()
    set_profile_field(char, "Title", "Trainer.")

    set_profile_field_privacy(char, "Title", True)
    assert get_profile_fields(char)["title"]["private"] is True

    with pytest.raises(ProfileError):
        set_profile_field_privacy(char, "Missing", True)

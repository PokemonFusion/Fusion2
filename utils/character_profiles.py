"""Shared helpers for player-facing character profile fields."""

from __future__ import annotations

import re
from collections import OrderedDict

PROFILE_ATTR = "profile_fields"
MAX_FIELD_LABEL_LENGTH = 32
MAX_FIELD_TEXT_LENGTH = 2000
STAFF_PRIVATE_PERMISSIONS = (
    "Helper",
    "Helpers",
    "Validator",
    "Validators",
    "Builder",
    "Builders",
    "Admin",
    "Admins",
    "Developer",
    "Developers",
    "Wizard",
    "Wizards",
)

_FIELD_KEY_RE = re.compile(r"[^a-z0-9_-]+")
_FIELD_LABEL_RE = re.compile(r"[^A-Za-z0-9 _-]+")
_SPACE_RE = re.compile(r"\s+")


class ProfileError(ValueError):
    """Raised when a profile operation cannot be completed."""


def field_key(label: str) -> str:
    """Return the stable storage key for a profile field label."""

    cleaned = _SPACE_RE.sub(" ", str(label or "").strip()).lower().replace(" ", "-")
    return _FIELD_KEY_RE.sub("", cleaned).strip("-_")


def clean_field_label(label: str) -> str:
    """Normalize a user-facing field label without making it cryptic."""

    cleaned = _FIELD_LABEL_RE.sub("", str(label or ""))
    cleaned = _SPACE_RE.sub(" ", cleaned).strip()
    if len(cleaned) > MAX_FIELD_LABEL_LENGTH:
        cleaned = cleaned[:MAX_FIELD_LABEL_LENGTH].rstrip()
    return cleaned


def clean_field_text(text: str) -> str:
    """Normalize profile body text while preserving intentional newlines."""

    cleaned = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if len(cleaned) > MAX_FIELD_TEXT_LENGTH:
        cleaned = cleaned[:MAX_FIELD_TEXT_LENGTH].rstrip()
    return cleaned


def _raw_fields(character):
    db = getattr(character, "db", None)
    raw = getattr(db, PROFILE_ATTR, None) if db is not None else None
    return raw if isinstance(raw, dict) else {}


def get_profile_fields(character) -> OrderedDict[str, dict]:
    """Return normalized profile fields for ``character``."""

    fields: OrderedDict[str, dict] = OrderedDict()
    for raw_key, raw_value in _raw_fields(character).items():
        if isinstance(raw_value, dict):
            label = clean_field_label(raw_value.get("label") or raw_key)
            text = clean_field_text(raw_value.get("text") or "")
            private = bool(raw_value.get("private", False))
        else:
            label = clean_field_label(raw_key)
            text = clean_field_text(raw_value)
            private = False

        key = field_key(label or raw_key)
        if not key or not text:
            continue
        fields[key] = {"label": label or key, "text": text, "private": private}
    return fields


def save_profile_fields(character, fields) -> OrderedDict[str, dict]:
    """Persist normalized profile fields on ``character``."""

    normalized = OrderedDict()
    for key, value in fields.items():
        label = clean_field_label(value.get("label") or key)
        text = clean_field_text(value.get("text") or "")
        normalized_key = field_key(label or key)
        if not normalized_key or not text:
            continue
        normalized[normalized_key] = {
            "label": label or normalized_key,
            "text": text,
            "private": bool(value.get("private", False)),
        }

    character.db.profile_fields = dict(normalized)
    return normalized


def set_profile_field(character, label: str, text: str, private: bool | None = None) -> dict:
    """Create or update a profile field."""

    cleaned_label = clean_field_label(label)
    key = field_key(cleaned_label)
    if not key:
        raise ProfileError("Field name must contain letters or numbers.")

    cleaned_text = clean_field_text(text)
    if not cleaned_text:
        raise ProfileError("Profile field text cannot be empty.")

    fields = get_profile_fields(character)
    existing = fields.get(key, {})
    fields[key] = {
        "label": cleaned_label,
        "text": cleaned_text,
        "private": bool(existing.get("private", False) if private is None else private),
    }
    save_profile_fields(character, fields)
    return fields[key]


def delete_profile_field(character, key_or_label: str) -> bool:
    """Delete a profile field by storage key or label."""

    fields = get_profile_fields(character)
    key = field_key(key_or_label)
    if key not in fields:
        return False
    del fields[key]
    save_profile_fields(character, fields)
    return True


def set_profile_field_privacy(character, key_or_label: str, private: bool) -> dict:
    """Set a field's privacy flag."""

    fields = get_profile_fields(character)
    key = field_key(key_or_label)
    if key not in fields:
        raise ProfileError("No such profile field.")
    fields[key]["private"] = bool(private)
    save_profile_fields(character, fields)
    return fields[key]


def _same_character(left, right) -> bool:
    if left is right:
        return True
    for attr in ("id", "dbref"):
        left_value = getattr(left, attr, None)
        right_value = getattr(right, attr, None)
        if left_value is not None and right_value is not None and left_value == right_value:
            return True
    return False


def _owns_character(account, character) -> bool:
    characters = getattr(account, "characters", None)
    if characters is None:
        return False
    try:
        owned = list(characters)
    except TypeError:
        owned = characters.all() if hasattr(characters, "all") else []
    except Exception:
        return False
    return any(_same_character(candidate, character) for candidate in owned if candidate)


def _check_perm(obj, perm: str) -> bool:
    check = getattr(obj, "check_permstring", None)
    if callable(check) and check(perm):
        return True

    account = getattr(obj, "account", None)
    check = getattr(account, "check_permstring", None)
    if callable(check) and check(perm):
        return True

    permissions = getattr(obj, "permissions", None)
    check = getattr(permissions, "check", None)
    return bool(callable(check) and check(perm))


def can_view_private_fields(viewer, owner) -> bool:
    """Return whether ``viewer`` can see private fields on ``owner``."""

    if _same_character(viewer, owner):
        return True
    if _owns_character(viewer, owner):
        return True
    return any(_check_perm(viewer, perm) for perm in STAFF_PRIVATE_PERMISSIONS)


def visible_profile_fields(character, viewer) -> OrderedDict[str, dict]:
    """Return profile fields visible to ``viewer``."""

    include_private = can_view_private_fields(viewer, character)
    fields = get_profile_fields(character)
    if include_private:
        return fields
    return OrderedDict((key, value) for key, value in fields.items() if not value["private"])

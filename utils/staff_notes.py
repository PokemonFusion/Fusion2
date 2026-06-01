"""Shared helpers for staff-only account and character notes."""

from __future__ import annotations

from datetime import datetime, timezone

from utils.staff_roster import account_id, account_name, is_staff_account


STAFF_NOTES_ATTR = "staff_notes"
MAX_STAFF_NOTE_TEXT_LENGTH = 1200


class StaffNoteError(ValueError):
    """Raised when a staff note operation cannot be completed."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clean_text(text: str, max_length: int = MAX_STAFF_NOTE_TEXT_LENGTH) -> str:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip()
    return cleaned


def _raw_notes(target) -> list:
    db = getattr(target, "db", None)
    notes = getattr(db, STAFF_NOTES_ATTR, None) if db is not None else None
    return notes if isinstance(notes, list) else []


def _note_id(note: dict) -> int:
    try:
        return int(note.get("id", 0))
    except (TypeError, ValueError):
        return 0


def _next_note_id(notes: list[dict]) -> int:
    return (max((_note_id(note) for note in notes), default=0) + 1)


def _normalize_note(note: dict) -> dict:
    return {
        "id": _note_id(note),
        "text": _clean_text(note.get("text", "")),
        "created_at": str(note.get("created_at") or ""),
        "author": str(note.get("author") or ""),
        "author_id": note.get("author_id"),
    }


def list_staff_notes(target) -> list[dict]:
    """Return normalized staff notes stored on ``target``."""

    notes = [_normalize_note(note) for note in _raw_notes(target) if isinstance(note, dict)]
    notes = [note for note in notes if note["id"] and note["text"]]
    return sorted(notes, key=lambda note: note["id"])


def save_staff_notes(target, notes: list[dict]) -> list[dict]:
    """Persist normalized staff notes on ``target``."""

    normalized = [_normalize_note(note) for note in notes if isinstance(note, dict)]
    normalized = [note for note in normalized if note["id"] and note["text"]]
    target.db.staff_notes = normalized
    return normalized


def add_staff_note(target, author_account, text: str) -> dict:
    """Add a staff-only note to an account or character."""

    if not is_staff_account(author_account):
        raise StaffNoteError("Only staff can add staff notes.")

    clean = _clean_text(text)
    if not clean:
        raise StaffNoteError("Note text cannot be empty.")

    notes = list_staff_notes(target)
    note = {
        "id": _next_note_id(notes),
        "text": clean,
        "created_at": _now(),
        "author": account_name(author_account),
        "author_id": account_id(author_account),
    }
    notes.append(note)
    save_staff_notes(target, notes)
    return note


def get_staff_note(target, note_id: int | str) -> dict:
    """Return a staff note by id."""

    try:
        needle = int(note_id)
    except (TypeError, ValueError):
        raise StaffNoteError("Note id must be a number.")

    for note in list_staff_notes(target):
        if note["id"] == needle:
            return note
    raise StaffNoteError(f"No note #{needle} found.")


def delete_staff_note(target, note_id: int | str) -> dict:
    """Delete a staff note by id and return the removed note."""

    note = get_staff_note(target, note_id)
    notes = [entry for entry in list_staff_notes(target) if entry["id"] != note["id"]]
    save_staff_notes(target, notes)
    return note

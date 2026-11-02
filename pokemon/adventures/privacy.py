"""Character-bound admission and observation policy for solo Adventures."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

PRIVATE_MESSAGE = "This solo Adventure is private."


class AdventurePrivacy:
    """Use persisted run identity; cached battle/session pointers grant no access."""

    @staticmethod
    def is_instance(room: Any) -> bool:
        """Recognize existing tagged rooms without changing their typeclasses."""
        value = getattr(getattr(room, "db", None), "adventure_instance", False)
        return value.lower() in {"true", "yes", "1", "on"} if isinstance(value, str) else bool(value)

    @staticmethod
    def staff_inspector(viewer: Any) -> bool:
        """Developer permission permits explicit inspection, independently of ownership."""
        try:
            checker = getattr(viewer, "check_permstring", None)
            return callable(checker) and checker("Developer") is True
        except Exception:
            return False

    @classmethod
    def room_access(cls, room: Any, viewer: Any) -> bool:
        """Only the reserved character or a Developer can enter/view an instance."""
        try:
            if not cls.is_instance(room):
                return True
            if cls.staff_inspector(viewer):
                return True
            from .sessions import _object_id, _query_first, _session_belongs_to_player, _session_model

            if _object_id(viewer) is None:
                return False
            session = _query_first(_session_model().objects.filter(instance_room=room, holds_instance=True))
            return session is not None and _session_belongs_to_player(session, viewer)
        except Exception:
            # Unavailable ownership storage never grants entry or aborts battle cleanup.
            return False

    @classmethod
    def battle_access(cls, battle: Any, viewer: Any) -> bool:
        """Apply the same policy to restored observers, direct selection and output."""
        try:
            metadata = getattr(battle, "encounter_metadata", None) or {}
            room = getattr(battle, "room", None)
            private = cls.is_instance(room) or (
                isinstance(metadata, Mapping) and metadata.get("source_type") == "adventure")
            if not private:
                return True
            if cls.staff_inspector(viewer):
                return True
            from .sessions import _session_belongs_to_player, _session_uses_room, get_session_by_id

            session_id = metadata.get("adventure_session_id") if isinstance(metadata, Mapping) else None
            if session_id is not None:
                session = get_session_by_id(session_id)
                return (session is not None and _session_belongs_to_player(session, viewer)
                        and _session_uses_room(session, room))
            return cls.room_access(room, viewer) if cls.is_instance(room) else False
        except Exception:
            # Observation is optional; result persistence/cleanup must remain retryable.
            return False

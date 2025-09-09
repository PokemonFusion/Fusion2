"""Database models for the room editor app."""
from __future__ import annotations

from django.db import models


class LockDefaults(models.Model):
    """Persist default lockstrings for rooms and exits."""

    id = models.SmallAutoField(primary_key=True)
    room_default = models.TextField(default="", blank=True)
    exit_default = models.TextField(default="", blank=True)

    @classmethod
    def get(cls) -> "LockDefaults":
        """Return the single defaults instance, creating if needed."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

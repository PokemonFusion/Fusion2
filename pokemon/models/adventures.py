"""Adventure session persistence models."""

from __future__ import annotations

from django.db import models
from django.utils import timezone
from evennia.objects.models import ObjectDB


class AdventureSession(models.Model):
    """Durable state for one active or recently completed adventure."""

    STATE_ACTIVE = "active"
    STATE_COMPLETED = "completed"
    STATE_ABANDONED = "abandoned"
    STATE_EXPIRED = "expired"

    STATE_CHOICES = (
        (STATE_ACTIVE, "Active"),
        (STATE_COMPLETED, "Completed"),
        (STATE_ABANDONED, "Abandoned"),
        (STATE_EXPIRED, "Expired"),
    )

    template_key = models.CharField(max_length=80, db_index=True)
    state = models.CharField(
        max_length=32,
        choices=STATE_CHOICES,
        default=STATE_ACTIVE,
        db_index=True,
    )
    leader = models.ForeignKey(
        ObjectDB,
        on_delete=models.SET_NULL,
        related_name="led_adventure_sessions",
        null=True,
        blank=True,
    )
    instance_room = models.ForeignKey(
        ObjectDB,
        on_delete=models.SET_NULL,
        related_name="adventure_instance_sessions",
        null=True,
        blank=True,
    )
    return_location = models.ForeignKey(
        ObjectDB,
        on_delete=models.SET_NULL,
        related_name="adventure_return_sessions",
        null=True,
        blank=True,
    )
    current_node = models.CharField(max_length=80)
    visited_nodes = models.JSONField(default=list, blank=True)
    objective_progress = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-started_at", "id")
        indexes = (
            models.Index(fields=("state", "template_key"), name="advsession_state_template_idx"),
            models.Index(fields=("leader", "state"), name="advsession_leader_state_idx"),
            models.Index(fields=("instance_room", "state"), name="advsession_room_state_idx"),
        )

    def __str__(self):  # pragma: no cover - simple representation
        return f"{self.template_key} for {self.leader or 'unknown'} ({self.state})"

    @property
    def is_active(self) -> bool:
        """Return whether this session should accept player actions."""

        return self.state == self.STATE_ACTIVE and self.completed_at is None

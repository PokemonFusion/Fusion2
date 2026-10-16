"""Persistent gym victories awaiting badge delivery."""

import uuid

from django.db import models
from django.utils import timezone
from evennia.objects.models import ObjectDB


class GymVictory(models.Model):
    """Keep one confirmed victory independently of its temporary battle room."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    player = models.ForeignKey(ObjectDB, on_delete=models.CASCADE, related_name="gym_victories")
    metadata = models.JSONField(default=dict)
    recorded_at = models.DateTimeField(default=timezone.now)
    claimed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("recorded_at", "id")
        indexes = (
            models.Index(fields=("player", "claimed_at"), name="gymvictory_player_claim_idx"),
        )

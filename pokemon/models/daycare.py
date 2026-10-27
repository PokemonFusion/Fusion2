"""Durable two-place Daycare custody without passive progression."""

from uuid import uuid4

from django.db import models


class DaycareEntry(models.Model):
    """Keep one existing owned Pokemon and an inspectable retrieval outcome."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    storage = models.ForeignKey("UserStorage", on_delete=models.CASCADE, related_name="daycare_entries")
    pokemon = models.ForeignKey("OwnedPokemon", null=True, on_delete=models.SET_NULL, related_name="daycare_entries")
    owned_id = models.UUIDField(db_index=True)
    saved_name = models.CharField(max_length=255)
    state = models.CharField(max_length=12, default="active", db_index=True)
    place = models.PositiveSmallIntegerField()
    preferred_party_slot = models.PositiveSmallIntegerField(null=True)
    fee = models.PositiveIntegerField(default=100)
    deposited_at = models.DateTimeField(auto_now_add=True)
    retrieved_at = models.DateTimeField(null=True)
    active_cycle = models.ForeignKey("BreedingCycle", null=True, on_delete=models.PROTECT, related_name="active_daycare_entries")
    receipt = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["pokemon"], condition=models.Q(state="active"), name="daycare_one_active_asset"),
            models.UniqueConstraint(fields=["storage", "place"], condition=models.Q(state="active"), name="daycare_place_unique"),
            models.CheckConstraint(condition=models.Q(place__in=(1, 2)), name="daycare_capacity_shape"),
            models.CheckConstraint(condition=(models.Q(state="active", pokemon__isnull=False, retrieved_at__isnull=True)
                | models.Q(state="retrieved", retrieved_at__isnull=False)), name="daycare_state_shape"),
        ]

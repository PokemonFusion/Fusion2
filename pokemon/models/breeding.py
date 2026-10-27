"""Durable one-outcome breeding cycles and same-identity hatch receipts."""

from uuid import uuid4

from django.db import models


class BreedingCycle(models.Model):
    """Seal one paid outcome and parent cooldown independently of later custody."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    storage = models.ForeignKey("UserStorage", null=True, on_delete=models.SET_NULL, related_name="breeding_cycles")
    origin_character_id = models.PositiveBigIntegerField(db_index=True)
    parent_a = models.ForeignKey("DaycareEntry", null=True, on_delete=models.SET_NULL, related_name="first_parent_cycles")
    parent_b = models.ForeignKey("DaycareEntry", null=True, on_delete=models.SET_NULL, related_name="second_parent_cycles")
    parent_a_uuid = models.UUIDField(db_index=True)
    parent_b_uuid = models.UUIDField(db_index=True)
    egg_uuid = models.UUIDField(default=uuid4, unique=True)
    state = models.CharField(max_length=12, default="producing", db_index=True)
    plan = models.JSONField()
    fee = models.PositiveIntegerField(default=500)
    started_at = models.DateTimeField()
    ready_at = models.DateTimeField()
    next_ready_at = models.DateTimeField(db_index=True)
    closed_at = models.DateTimeField(null=True)
    receipt = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["storage"], condition=models.Q(state="producing"), name="breeding_one_active_cycle"),
            models.CheckConstraint(condition=~models.Q(parent_a_uuid=models.F("parent_b_uuid")), name="breeding_distinct_parents"),
            models.CheckConstraint(condition=(models.Q(state="producing", storage__isnull=False, parent_a__isnull=False, parent_b__isnull=False, closed_at__isnull=True)
                | models.Q(state__in=("collected", "cancelled"), closed_at__isnull=False)), name="breeding_cycle_shape"),
            models.CheckConstraint(condition=models.Q(ready_at__gte=models.F("started_at"), next_ready_at__gte=models.F("ready_at")), name="breeding_deadline_order"),
        ]


class BreedingEgg(models.Model):
    """Track the planned owned UUID through collection, trading, hatch and release."""

    id = models.UUIDField(primary_key=True, editable=False)
    cycle = models.OneToOneField(BreedingCycle, on_delete=models.PROTECT, related_name="egg_record")
    pokemon = models.OneToOneField("OwnedPokemon", null=True, on_delete=models.SET_NULL, related_name="bred_egg_record")
    collected_at = models.DateTimeField()
    hatch_ready_at = models.DateTimeField(db_index=True)
    hatched_at = models.DateTimeField(null=True)
    hatch_owner_id = models.PositiveBigIntegerField(null=True)
    hatch_receipt = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(hatch_ready_at__gte=models.F("collected_at")), name="breeding_hatch_deadline"),
            models.CheckConstraint(condition=(models.Q(hatched_at__isnull=True, hatch_owner_id__isnull=True)
                | models.Q(hatched_at__isnull=False, hatch_owner_id__isnull=False)), name="breeding_hatch_shape"),
        ]

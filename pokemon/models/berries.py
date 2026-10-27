"""One durable, private Oran Berry growing cycle per trainer."""

from django.db import models


class BerryBed(models.Model):
    """Keep growth and the last completed receipt separate from bag inventory."""

    trainer = models.OneToOneField("Trainer", on_delete=models.CASCADE, related_name="berry_bed")
    cycle_id = models.UUIDField(null=True, blank=True)
    berry = models.CharField(max_length=40, blank=True)
    planted_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    watered_mask = models.PositiveSmallIntegerField(default=0)
    last_harvest_cycle = models.UUIDField(null=True, blank=True)
    last_harvest_yield = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(watered_mask__lte=15), name="berrybed_water_mask"),
            models.CheckConstraint(condition=models.Q(last_harvest_yield__lte=5), name="berrybed_harvest_yield"),
        ]

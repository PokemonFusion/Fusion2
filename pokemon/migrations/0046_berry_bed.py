"""Define the owned Oran bed; applying this to a running world is separate."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Add no inventory grants, timers, world content or existing-data writes."""

    dependencies = [("pokemon", "0045_production_strategy_gym")]
    operations = [
        migrations.CreateModel(
            name="BerryBed",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cycle_id", models.UUIDField(blank=True, null=True)),
                ("berry", models.CharField(blank=True, max_length=40)),
                ("planted_at", models.DateTimeField(blank=True, null=True)),
                ("ready_at", models.DateTimeField(blank=True, null=True)),
                ("watered_mask", models.PositiveSmallIntegerField(default=0)),
                ("last_harvest_cycle", models.UUIDField(blank=True, null=True)),
                ("last_harvest_yield", models.PositiveSmallIntegerField(default=0)),
                ("trainer", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,
                                                  related_name="berry_bed", to="pokemon.trainer")),
            ],
            options={"constraints": [
                models.CheckConstraint(condition=models.Q(watered_mask__lte=15), name="berrybed_water_mask"),
                models.CheckConstraint(condition=models.Q(last_harvest_yield__lte=5), name="berrybed_harvest_yield"),
            ]},
        ),
    ]

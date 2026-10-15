"""Retain gym victories until badge delivery commits successfully."""

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    """Add the durable, character-scoped gym victory ledger."""

    dependencies = [("pokemon", "0042_merge_adventure_placement")]

    operations = [
        migrations.CreateModel(
            name="GymVictory",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("metadata", models.JSONField(default=dict)),
                ("recorded_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("claimed_at", models.DateTimeField(blank=True, null=True)),
                ("player", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="gym_victories", to="objects.objectdb",
                )),
            ],
            options={
                "ordering": ("recorded_at", "id"),
                "indexes": [models.Index(fields=["player", "claimed_at"], name="gymvictory_player_claim_idx")],
            },
        ),
    ]

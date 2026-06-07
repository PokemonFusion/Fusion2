# Generated manually for the Adventure System MVP.

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("objects", "0013_defaultobject_alter_objectdb_id_defaultcharacter_and_more"),
        ("pokemon", "0038_gym_leader_profile"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdventureSession",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("template_key", models.CharField(db_index=True, max_length=80)),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("completed", "Completed"),
                            ("abandoned", "Abandoned"),
                            ("expired", "Expired"),
                        ],
                        db_index=True,
                        default="active",
                        max_length=32,
                    ),
                ),
                ("current_node", models.CharField(max_length=80)),
                ("visited_nodes", models.JSONField(blank=True, default=list)),
                ("objective_progress", models.JSONField(blank=True, default=dict)),
                (
                    "started_at",
                    models.DateTimeField(default=django.utils.timezone.now, db_index=True),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("expires_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "instance_room",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="adventure_instance_sessions",
                        to="objects.objectdb",
                    ),
                ),
                (
                    "leader",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="led_adventure_sessions",
                        to="objects.objectdb",
                    ),
                ),
                (
                    "return_location",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="adventure_return_sessions",
                        to="objects.objectdb",
                    ),
                ),
            ],
            options={
                "ordering": ("-started_at", "id"),
                "indexes": [
                    models.Index(
                        fields=["state", "template_key"],
                        name="advsession_state_template_idx",
                    ),
                    models.Index(
                        fields=["leader", "state"],
                        name="advsession_leader_state_idx",
                    ),
                    models.Index(
                        fields=["instance_room", "state"],
                        name="advsession_room_state_idx",
                    ),
                ],
            },
        ),
    ]

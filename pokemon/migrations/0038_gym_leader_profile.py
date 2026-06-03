from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("pokemon", "0037_remove_ownedpokemon_temp_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="GymLeaderProfile",
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
                ("league_key", models.CharField(db_index=True, max_length=80)),
                ("gym_key", models.CharField(db_index=True, max_length=80)),
                ("badge_key", models.CharField(db_index=True, max_length=80)),
                ("required_badge_count", models.PositiveSmallIntegerField(default=0)),
                ("is_enabled", models.BooleanField(db_index=True, default=True)),
                ("sort_order", models.PositiveSmallIntegerField(db_index=True, default=1)),
                (
                    "badge",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="gym_leader_profiles",
                        to="pokemon.gymbadge",
                    ),
                ),
                (
                    "npc_trainer",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="gym_leader_profile",
                        to="pokemon.npctrainer",
                    ),
                ),
            ],
            options={
                "ordering": ("sort_order", "league_key", "gym_key"),
                "constraints": [
                    models.UniqueConstraint(
                        fields=("league_key", "gym_key"),
                        name="gymleaderprofile_unique_gym",
                    ),
                    models.UniqueConstraint(
                        fields=("league_key", "badge_key"),
                        name="gymleaderprofile_unique_badge_key",
                    ),
                ],
            },
        ),
    ]

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [("pokemon", "0039_adventure_session")]

    operations = [
        migrations.CreateModel(
            name="AdventureParticipation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("route_key", models.CharField(blank=True, max_length=80)),
                ("outcome_key", models.CharField(blank=True, max_length=80)),
                ("encounter_result", models.CharField(blank=True, max_length=32)),
                ("joined_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("completed_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("reward_item", models.CharField(blank=True, max_length=80)),
                ("reward_amount", models.PositiveIntegerField(default=0)),
                ("reward_claimed_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("player", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="adventure_participations", to="objects.objectdb")),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="participations", to="pokemon.adventuresession")),
            ],
        ),
        migrations.AddConstraint(
            model_name="adventureparticipation",
            constraint=models.UniqueConstraint(fields=("session", "player"), name="adventure_participation_session_player_uniq"),
        ),
        migrations.AddIndex(
            model_name="adventureparticipation",
            index=models.Index(fields=["player", "completed_at"], name="advpart_player_completed_idx"),
        ),
    ]

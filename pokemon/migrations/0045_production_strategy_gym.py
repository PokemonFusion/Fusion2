"""Persist bounded gym configuration and first-clear/rematch delivery results."""

from django.db import migrations, models


def mark_alpha_test_content(apps, schema_editor):
    """Keep installed Alpha content out of the normal production gym list."""
    profile = apps.get_model("pokemon", "GymLeaderProfile")
    profile.objects.filter(league_key="alpha", gym_key="alpha_gym").update(content_stage="test")


class Migration(migrations.Migration):
    """Add configuration without replacing roster rows or existing victories."""

    dependencies = [("pokemon", "0044_owned_pokemon_status")]
    operations = [
        migrations.AddField("gymleaderprofile", "battle_format", models.CharField(max_length=10, default="single", choices=[("single", "Singles"), ("double", "Doubles")])),
        migrations.AddField("gymleaderprofile", "ai_profile", models.CharField(max_length=80, default="gym_leader")),
        migrations.AddField("gymleaderprofile", "strategy_key", models.CharField(max_length=40, blank=True, default="", choices=[("", "None"), ("trick_room", "Trick Room")])),
        migrations.AddField("gymleaderprofile", "content_stage", models.CharField(max_length=16, default="production", choices=[("production", "Production"), ("test", "Test")])),
        migrations.AddField("gymleaderprofile", "intro_text", models.TextField(blank=True)),
        migrations.AddField("gymleaderprofile", "victory_text", models.TextField(blank=True)),
        migrations.AddField("gymleaderprofile", "defeat_text", models.TextField(blank=True)),
        migrations.AddField("gymleaderprofile", "rules_text", models.TextField(blank=True)),
        migrations.AddField("gymleaderprofile", "reward_policy", models.CharField(max_length=16, default="legacy", choices=[("legacy", "Legacy"), ("badge_only", "Badge only")])),
        migrations.AddField("gymleaderprofile", "rematch_cooldown_seconds", models.PositiveIntegerField(default=0)),
        migrations.AddField("gymvictory", "award_kind", models.CharField(max_length=16, blank=True, default="", choices=[("first_clear", "First clear"), ("rematch", "Rematch")])),
        migrations.RunPython(mark_alpha_test_content, migrations.RunPython.noop),
    ]

"""Retain major status conditions and sleep progress between battles."""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Add durable status fields; existing Pokémon start without a condition."""

    dependencies = [("pokemon", "0043_gym_victory")]

    operations = [
        migrations.AddField(
            model_name="ownedpokemon",
            name="status",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="ownedpokemon",
            name="sleep_turns",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pokemon", "0021_pokemon_fusion"),
    ]

    operations = [
        migrations.AddField(
            model_name="ownedpokemon",
            name="movesets",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="ownedpokemon",
            name="active_moveset_index",
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]

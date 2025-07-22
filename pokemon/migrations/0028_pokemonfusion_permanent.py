from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pokemon", "0027_trainer_pokemon_fusion"),
    ]

    operations = [
        migrations.AddField(
            model_name="pokemonfusion",
            name="permanent",
            field=models.BooleanField(default=False, db_index=True),
        ),
    ]

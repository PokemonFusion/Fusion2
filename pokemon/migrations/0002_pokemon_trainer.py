from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ("pokemon", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="pokemon",
            name="trainer",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="owned_pokemon",
                null=True,
                blank=True,
                to="pokemon.trainer",
            ),
        ),
    ]

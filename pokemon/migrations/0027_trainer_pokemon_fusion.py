from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("pokemon", "0026_ordered_unique_fusion"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="pokemonfusion",
            name="unique_fusion_parents",
        ),
        migrations.RemoveConstraint(
            model_name="pokemonfusion",
            name="ordered_fusion_parents",
        ),
        migrations.RemoveField(
            model_name="pokemonfusion",
            name="parent_a",
        ),
        migrations.RemoveField(
            model_name="pokemonfusion",
            name="parent_b",
        ),
        migrations.AddField(
            model_name="pokemonfusion",
            name="trainer",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="pokemon_fusions",
                to="pokemon.trainer",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="pokemonfusion",
            name="pokemon",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="trainer_fusions",
                to="pokemon.ownedpokemon",
                null=True,
            ),
        ),
        migrations.AddConstraint(
            model_name="pokemonfusion",
            constraint=models.UniqueConstraint(
                fields=["trainer", "pokemon"],
                name="unique_trainer_pokemon_fusion",
            ),
        ),
    ]

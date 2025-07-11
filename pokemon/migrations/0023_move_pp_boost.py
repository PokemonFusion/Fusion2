from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pokemon", "0022_movesets"),
    ]

    operations = [
        migrations.CreateModel(
            name="MovePPBoost",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "bonus_pp",
                    models.PositiveSmallIntegerField(default=0),
                ),
                (
                    "move",
                    models.ForeignKey(on_delete=models.CASCADE, to="pokemon.move"),
                ),
                (
                    "pokemon",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="pp_boosts",
                        to="pokemon.ownedpokemon",
                    ),
                ),
            ],
            options={
                "unique_together": {("pokemon", "move")},
            },
        ),
    ]

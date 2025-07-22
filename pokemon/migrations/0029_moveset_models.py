from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("pokemon", "0028_pokemonfusion_permanent"),
    ]

    operations = [
        migrations.RenameField(
            model_name="ownedpokemon",
            old_name="active_moveset",
            new_name="active_moves",
        ),
        migrations.CreateModel(
            name="Moveset",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("pokemon", models.ForeignKey(on_delete=models.CASCADE, related_name="movesets", to="pokemon.ownedpokemon")),
                ("index", models.PositiveSmallIntegerField()),
            ],
            options={"unique_together": {("pokemon", "index")}},
        ),
        migrations.CreateModel(
            name="MovesetSlot",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slot", models.PositiveSmallIntegerField()),
                ("move", models.ForeignKey(on_delete=models.CASCADE, to="pokemon.move")),
                ("moveset", models.ForeignKey(on_delete=models.CASCADE, related_name="slots", to="pokemon.moveset")),
            ],
            options={"unique_together": {("moveset", "slot")}},
        ),
        migrations.AddField(
            model_name="ownedpokemon",
            name="active_moveset",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="active_for", to="pokemon.moveset"),
        ),
        migrations.RemoveField(
            model_name="ownedpokemon",
            name="movesets",
        ),
        migrations.RemoveField(
            model_name="ownedpokemon",
            name="active_moveset_index",
        ),
    ]

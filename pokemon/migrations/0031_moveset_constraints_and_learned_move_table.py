from django.db import migrations, models
import django.db.models.deletion


def copy_learned_moves_forwards(apps, schema_editor):
    OwnedPokemon = apps.get_model("pokemon", "OwnedPokemon")
    for pokemon in OwnedPokemon.objects.all():
        for move in pokemon.learned_moves.all():
            pokemon.learned_moves_new.add(move)


class Migration(migrations.Migration):

    dependencies = [
        ("pokemon", "0030_alter_moveset_id_alter_movesetslot_id_and_more"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="moveset",
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name="movesetslot",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="moveset",
            constraint=models.UniqueConstraint(
                fields=["pokemon", "index"],
                name="unique_moveset_index",
            ),
        ),
        migrations.AddConstraint(
            model_name="moveset",
            constraint=models.CheckConstraint(
                check=models.Q(index__gte=0, index__lte=3),
                name="moveset_index_range",
            ),
        ),
        migrations.AddConstraint(
            model_name="movesetslot",
            constraint=models.UniqueConstraint(
                fields=["moveset", "slot"],
                name="unique_moveset_slot",
            ),
        ),
        migrations.AddConstraint(
            model_name="movesetslot",
            constraint=models.CheckConstraint(
                check=models.Q(slot__gte=1, slot__lte=4),
                name="movesetslot_slot_range",
            ),
        ),
        migrations.RemoveField(
            model_name="ownedpokemon",
            name="active_moves",
        ),
        migrations.CreateModel(
            name="PokemonLearnedMove",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("pokemon", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, db_index=True, to="pokemon.ownedpokemon")),
                ("move", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, db_index=True, to="pokemon.move")),
            ],
            options={
                "unique_together": {("pokemon", "move")},
                "indexes": [
                    models.Index(
                        fields=["pokemon"], name="pokemonlearnedmove_pokemon_idx"
                    ),
                    models.Index(fields=["move"], name="pokemonlearnedmove_move_idx"),
                ],
            },
        ),
        migrations.AddField(
            model_name="ownedpokemon",
            name="learned_moves_new",
            field=models.ManyToManyField(
                related_name="owners_new",
                through="pokemon.PokemonLearnedMove",
                to="pokemon.move",
            ),
        ),
        migrations.RunPython(
            code=copy_learned_moves_forwards,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="ownedpokemon",
            name="learned_moves",
        ),
        migrations.RenameField(
            model_name="ownedpokemon",
            old_name="learned_moves_new",
            new_name="learned_moves",
        ),
        migrations.AlterField(
            model_name="ownedpokemon",
            name="learned_moves",
            field=models.ManyToManyField(
                related_name="owners",
                through="pokemon.PokemonLearnedMove",
                to="pokemon.move",
            ),
        ),
    ]

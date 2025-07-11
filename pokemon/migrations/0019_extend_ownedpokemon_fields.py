from django.db import migrations, models
import django.contrib.postgres.fields
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ("pokemon", "0018_inventory_entry"),
    ]

    operations = [
        migrations.AddField(
            model_name="ownedpokemon",
            name="is_shiny",
            field=models.BooleanField(default=False, db_index=True),
        ),
        migrations.AddField(
            model_name="ownedpokemon",
            name="met_location",
            field=models.CharField(max_length=100, blank=True),
        ),
        migrations.AddField(
            model_name="ownedpokemon",
            name="met_level",
            field=models.PositiveSmallIntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="ownedpokemon",
            name="met_date",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="ownedpokemon",
            name="obtained_method",
            field=models.CharField(max_length=50, blank=True),
        ),
        migrations.AddField(
            model_name="ownedpokemon",
            name="original_trainer",
            field=models.ForeignKey(
                related_name="original_pokemon",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="pokemon.trainer",
            ),
        ),
        migrations.AddField(
            model_name="ownedpokemon",
            name="original_trainer_name",
            field=models.CharField(max_length=100, blank=True),
        ),
        migrations.AddField(
            model_name="ownedpokemon",
            name="is_egg",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="ownedpokemon",
            name="hatch_steps",
            field=models.PositiveIntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="ownedpokemon",
            name="friendship",
            field=models.PositiveSmallIntegerField(default=70),
        ),
        migrations.AddField(
            model_name="ownedpokemon",
            name="flags",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=50),
                default=list,
                size=None,
                blank=True,
            ),
        ),
    ]

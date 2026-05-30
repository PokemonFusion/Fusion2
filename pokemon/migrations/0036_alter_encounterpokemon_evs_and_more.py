from django.db import migrations, models
import django.contrib.postgres.fields

import pokemon.models.validators


class Migration(migrations.Migration):

    dependencies = [
        ("pokemon", "0035_encounterpokemon_npctemplate_pokemonplacement"),
    ]

    operations = [
        migrations.AlterField(
            model_name="encounterpokemon",
            name="evs",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.PositiveSmallIntegerField(),
                default=list,
                size=6,
                validators=[pokemon.models.validators.validate_evs],
            ),
        ),
        migrations.AlterField(
            model_name="encounterpokemon",
            name="gender",
            field=models.CharField(
                blank=True,
                choices=[("M", "Male"), ("F", "Female"), ("N", "None")],
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="encounterpokemon",
            name="ivs",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.PositiveSmallIntegerField(),
                default=list,
                size=6,
                validators=[pokemon.models.validators.validate_ivs],
            ),
        ),
        migrations.AlterField(
            model_name="encounterpokemon",
            name="nature",
            field=models.CharField(
                blank=True,
                choices=[
                    ("Hardy", "Hardy"),
                    ("Lonely", "Lonely"),
                    ("Brave", "Brave"),
                    ("Adamant", "Adamant"),
                    ("Naughty", "Naughty"),
                    ("Bold", "Bold"),
                    ("Docile", "Docile"),
                    ("Relaxed", "Relaxed"),
                    ("Impish", "Impish"),
                    ("Lax", "Lax"),
                    ("Timid", "Timid"),
                    ("Hasty", "Hasty"),
                    ("Serious", "Serious"),
                    ("Jolly", "Jolly"),
                    ("Naive", "Naive"),
                    ("Modest", "Modest"),
                    ("Mild", "Mild"),
                    ("Quiet", "Quiet"),
                    ("Bashful", "Bashful"),
                    ("Rash", "Rash"),
                    ("Calm", "Calm"),
                    ("Gentle", "Gentle"),
                    ("Sassy", "Sassy"),
                    ("Careful", "Careful"),
                    ("Quirky", "Quirky"),
                ],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="npcpokemontemplate",
            name="evs",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.PositiveSmallIntegerField(),
                default=list,
                size=6,
                validators=[pokemon.models.validators.validate_evs],
            ),
        ),
        migrations.AlterField(
            model_name="npcpokemontemplate",
            name="ivs",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.PositiveSmallIntegerField(),
                default=list,
                size=6,
                validators=[pokemon.models.validators.validate_ivs],
            ),
        ),
    ]

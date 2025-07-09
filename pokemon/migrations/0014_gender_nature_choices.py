from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pokemon", "0013_species_entry"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ownedpokemon",
            name="gender",
            field=models.CharField(blank=True, max_length=10, choices=[("M", "Male"), ("F", "Female"), ("N", "None")]),
        ),
        migrations.AlterField(
            model_name="ownedpokemon",
            name="nature",
            field=models.CharField(blank=True, max_length=20, choices=[
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
            ]),
        ),
        migrations.AlterField(
            model_name="npctrainerpokemon",
            name="gender",
            field=models.CharField(blank=True, max_length=10, choices=[("M", "Male"), ("F", "Female"), ("N", "None")]),
        ),
        migrations.AlterField(
            model_name="npctrainerpokemon",
            name="nature",
            field=models.CharField(blank=True, max_length=20, choices=[
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
            ]),
        ),
    ]

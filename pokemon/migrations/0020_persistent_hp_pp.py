from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("pokemon", "0019_extend_ownedpokemon_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="ownedpokemon",
            name="current_hp",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="activemoveslot",
            name="current_pp",
            field=models.PositiveSmallIntegerField(null=True, blank=True),
        ),
    ]

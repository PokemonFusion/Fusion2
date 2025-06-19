from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pokemon", "0003_trainer_badges"),
    ]

    operations = [
        migrations.AddField(
            model_name="pokemon",
            name="data",
            field=models.JSONField(default=dict, blank=True),
        ),
    ]

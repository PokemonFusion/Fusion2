from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pokemon", "0031_moveset_constraints_and_learned_move_table"),
    ]

    operations = [
        migrations.AddField(
            model_name="move",
            name="verified",
            field=models.BooleanField(default=False),
        ),
    ]

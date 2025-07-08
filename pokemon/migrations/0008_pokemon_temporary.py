from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pokemon', '0007_add_held_item'),
    ]

    operations = [
        migrations.AddField(
            model_name='pokemon',
            name='temporary',
            field=models.BooleanField(default=False, db_index=True),
        ),
    ]
